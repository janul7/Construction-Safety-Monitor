from typing import Dict, List, Optional, Sequence, Set, Tuple

import yaml

from src.schemas import Detection, WorkerAssessment

Point = Tuple[float, float]
Polygon = List[Point]


def load_rules(rules_path: str) -> Dict:
    with open(rules_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def box_center(box: Tuple[float, float, float, float]) -> Point:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def box_area(box: Tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def point_in_box(point: Point, box: Tuple[float, float, float, float]) -> bool:
    px, py = point
    x1, y1, x2, y2 = box
    return x1 <= px <= x2 and y1 <= py <= y2


def iou(box_a: Tuple[float, float, float, float], box_b: Tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_area = box_area((inter_x1, inter_y1, inter_x2, inter_y2))
    union = box_area(box_a) + box_area(box_b) - inter_area

    if union <= 0:
        return 0.0
    return inter_area / union


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """
    Ray-casting algorithm.
    """
    x, y = point
    inside = False
    n = len(polygon)

    if n < 3:
        return False

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) + 1e-9) + xi
        )
        if intersects:
            inside = not inside
        j = i

    return inside


def denormalize_polygon(polygon: Sequence[Sequence[float]], width: int, height: int) -> Polygon:
    return [(float(x) * width, float(y) * height) for x, y in polygon]


def make_region(
    person_box: Tuple[float, float, float, float],
    top_ratio: float,
    bottom_ratio: float,
    side_padding_ratio: float,
) -> Tuple[float, float, float, float]:
    x1, y1, x2, y2 = person_box
    width = x2 - x1
    height = y2 - y1

    rx1 = x1 + side_padding_ratio * width
    rx2 = x2 - side_padding_ratio * width
    ry1 = y1 + top_ratio * height
    ry2 = y1 + bottom_ratio * height

    return (rx1, ry1, rx2, ry2)


def touches_frame_edge(
    box: Tuple[float, float, float, float],
    frame_width: int,
    frame_height: int,
    edge_margin: int = 2,
) -> bool:
    x1, y1, x2, y2 = box
    return x1 <= edge_margin or y1 <= edge_margin or x2 >= frame_width - edge_margin or y2 >= frame_height - edge_margin


def get_zone_name_and_required_ppe(
    person_box: Tuple[float, float, float, float],
    zones: List[Dict],
    default_required_ppe: List[str],
    frame_width: int,
    frame_height: int,
) -> Tuple[str, List[str]]:
    center = box_center(person_box)

    for zone in zones:
        if not zone.get("enabled", True):
            continue

        polygon = zone.get("polygon", [])
        if not polygon:
            return zone.get("name", "full_frame"), zone.get("required_ppe", default_required_ppe)

        denorm = denormalize_polygon(polygon, frame_width, frame_height)
        if point_in_polygon(center, denorm):
            return zone.get("name", "zone"), zone.get("required_ppe", default_required_ppe)

    return "default", default_required_ppe


def find_best_candidate(
    person_box: Tuple[float, float, float, float],
    candidates: List[Detection],
    used_indices: Set[int],
    region_box: Tuple[float, float, float, float],
    min_conf: float,
) -> Optional[Detection]:
    best_index: Optional[int] = None
    best_score = -1.0

    for i, det in enumerate(candidates):
        if i in used_indices:
            continue
        if det.confidence < min_conf:
            continue

        center = box_center(det.box)
        if not point_in_box(center, region_box):
            continue

        overlap = iou(det.box, person_box)
        horizontal_alignment = 1.0 if person_box[0] <= center[0] <= person_box[2] else 0.0

        score = (0.60 * det.confidence) + (0.25 * overlap) + (0.15 * horizontal_alignment)

        if score > best_score:
            best_score = score
            best_index = i

    if best_index is None:
        return None

    used_indices.add(best_index)
    return candidates[best_index]


def scene_status_from_workers(worker_reports: List[WorkerAssessment]) -> str:
    if any(worker.status == "VIOLATION" for worker in worker_reports):
        return "UNSAFE"
    if any(worker.status == "UNCERTAIN" for worker in worker_reports):
        return "REVIEW"
    return "SAFE"


def evaluate_detections(
    detections: List[Detection],
    frame_shape: Tuple[int, int, int],
    rules: Dict,
) -> Tuple[List[WorkerAssessment], str, Dict]:
    frame_height, frame_width = frame_shape[:2]
    frame_area = float(frame_width * frame_height)

    class_map = rules["model"]["class_map"]
    thresholds = rules["thresholds"]
    association = rules["association"]
    policy = rules["policy"]
    zones = rules.get("zones", [])

    persons = [
        det for det in detections
        if det.class_id == class_map["person"] and det.confidence >= thresholds["person_conf"]
    ]
    helmets = [
        det for det in detections
        if det.class_id == class_map["helmet"] and det.confidence >= thresholds["helmet_conf"]
    ]
    vests = [
        det for det in detections
        if det.class_id == class_map["vest"] and det.confidence >= thresholds["vest_conf"]
    ]

    used_helmets: Set[int] = set()
    used_vests: Set[int] = set()
    worker_reports: List[WorkerAssessment] = []

    default_required_ppe = policy.get("default_required_ppe", ["helmet", "vest"])

    for worker_index, person in enumerate(persons):
        zone_name, required_ppe = get_zone_name_and_required_ppe(
            person_box=person.box,
            zones=zones,
            default_required_ppe=default_required_ppe,
            frame_width=frame_width,
            frame_height=frame_height,
        )

        notes: List[str] = []
        violations: List[str] = []

        area_ratio = box_area(person.box) / max(frame_area, 1.0)
        if area_ratio < thresholds["min_person_area_ratio"]:
            notes.append("person_too_small_for_reliable_ppe_check")

        if touches_frame_edge(person.box, frame_width, frame_height):
            notes.append("person_truncated_at_frame_edge")

        helmet_region = make_region(
            person_box=person.box,
            top_ratio=0.0,
            bottom_ratio=association["helmet_top_ratio"],
            side_padding_ratio=association["side_padding_ratio"],
        )

        vest_region = make_region(
            person_box=person.box,
            top_ratio=association["vest_top_ratio"],
            bottom_ratio=association["vest_bottom_ratio"],
            side_padding_ratio=association["side_padding_ratio"],
        )

        helmet_match = None
        vest_match = None

        if "helmet" in required_ppe:
            helmet_match = find_best_candidate(
                person_box=person.box,
                candidates=helmets,
                used_indices=used_helmets,
                region_box=helmet_region,
                min_conf=thresholds["helmet_conf"],
            )
            if helmet_match is None:
                violations.append("missing_helmet")

        if "vest" in required_ppe:
            vest_match = find_best_candidate(
                person_box=person.box,
                candidates=vests,
                used_indices=used_vests,
                region_box=vest_region,
                min_conf=thresholds["vest_conf"],
            )
            if vest_match is None:
                violations.append("missing_vest")

        status = "COMPLIANT"
        if violations:
            status = "VIOLATION"
        elif notes:
            status = "UNCERTAIN"

        if notes and policy.get("mark_uncertain_as_violation", False) and not violations:
            status = "VIOLATION"
            violations.append("uncertain_visibility_policy")

        worker_reports.append(
            WorkerAssessment(
                worker_index=worker_index,
                track_id=person.track_id,
                person_box=person.box,
                person_confidence=person.confidence,
                zone_name=zone_name,
                required_ppe=required_ppe,
                helmet_detected=helmet_match is not None,
                vest_detected=vest_match is not None,
                helmet_confidence=helmet_match.confidence if helmet_match else None,
                vest_confidence=vest_match.confidence if vest_match else None,
                status=status,
                violations=violations,
                notes=notes,
            )
        )

    scene_status = scene_status_from_workers(worker_reports)

    summary = {
        "total_workers": len(worker_reports),
        "compliant_workers": sum(worker.status == "COMPLIANT" for worker in worker_reports),
        "violating_workers": sum(worker.status == "VIOLATION" for worker in worker_reports),
        "uncertain_workers": sum(worker.status == "UNCERTAIN" for worker in worker_reports),
    }

    return worker_reports, scene_status, summary