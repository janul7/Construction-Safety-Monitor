import json
from pathlib import Path
from typing import Dict, List

import cv2
from ultralytics import YOLO

from src.rules import evaluate_detections, load_rules, scene_status_from_workers
from src.schemas import Detection, FrameReport, WorkerAssessment
from src.smoother import TemporalSmoother


class SafetyMonitor:
    def __init__(self, model_path: str, rules_path: str) -> None:
        self.model = YOLO(model_path)
        self.rules = load_rules(rules_path)

        thresholds = self.rules["thresholds"]
        self.predict_conf = min(
            thresholds["person_conf"],
            thresholds["helmet_conf"],
            thresholds["vest_conf"],
        )

        video_cfg = self.rules.get("video", {})
        self.use_tracking = bool(video_cfg.get("use_tracking", True))
        self.tracker = video_cfg.get("tracker", "bytetrack.yaml")
        self.smoother = TemporalSmoother(
            window_size=int(video_cfg.get("smoothing_window", 7)),
            min_violation_votes=int(video_cfg.get("min_violation_votes", 4)),
        )

    def _result_to_detections(self, result) -> List[Detection]:
        detections: List[Detection] = []

        if result.boxes is None or len(result.boxes) == 0:
            return detections

        boxes = result.boxes
        xyxy = boxes.xyxy.cpu().tolist()
        confs = boxes.conf.cpu().tolist()
        classes = boxes.cls.int().cpu().tolist()

        if boxes.id is not None:
            track_ids = boxes.id.int().cpu().tolist()
        else:
            track_ids = [None] * len(xyxy)

        for box, conf, class_id, track_id in zip(xyxy, confs, classes, track_ids):
            detections.append(
                Detection(
                    class_id=int(class_id),
                    class_name=str(result.names[int(class_id)]),
                    confidence=float(conf),
                    box=tuple(float(v) for v in box),
                    track_id=int(track_id) if track_id is not None else None,
                )
            )

        return detections

    def _infer_frame(self, frame, use_tracking: bool) -> List[Detection]:
        if use_tracking:
            result = self.model.track(
                frame,
                conf=self.predict_conf,
                persist=True,
                tracker=self.tracker,
                verbose=False,
            )[0]
        else:
            result = self.model.predict(
                frame,
                conf=self.predict_conf,
                verbose=False,
            )[0]

        return self._result_to_detections(result)

    def analyze_frame(
        self, frame, use_tracking: bool = False,
    ) -> tuple:
        """Run detection and rule evaluation on a single frame.

        Returns (workers, scene_status, summary).
        """
        detections = self._infer_frame(frame, use_tracking)
        workers, scene_status, summary = evaluate_detections(
            detections, frame.shape, self.rules,
        )
        if use_tracking:
            workers = self.smoother.update(workers)
            scene_status = scene_status_from_workers(workers)
        return workers, scene_status, summary

    def reset_tracking(self) -> None:
        """Reset temporal smoother state. Call between separate videos."""
        self.smoother = TemporalSmoother(
            window_size=self.smoother.window_size,
            min_violation_votes=self.smoother.min_violation_votes,
        )

    def _color_for_status(self, status: str):
        if status == "COMPLIANT":
            return (0, 200, 0)      # green
        if status == "VIOLATION":
            return (0, 0, 255)      # red
        return (0, 215, 255)        # yellow

    def annotate_frame(self, frame, workers: List[WorkerAssessment], scene_status: str):
        annotated = frame.copy()

        header_color = {
            "SAFE": (0, 200, 0),
            "UNSAFE": (0, 0, 255),
            "REVIEW": (0, 215, 255),
        }.get(scene_status, (255, 255, 255))

        cv2.rectangle(annotated, (10, 10), (310, 50), header_color, -1)
        cv2.putText(
            annotated,
            f"Scene: {scene_status}",
            (20, 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )

        for worker in workers:
            x1, y1, x2, y2 = [int(v) for v in worker.person_box]
            color = self._color_for_status(worker.status)

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            worker_id = f"ID:{worker.track_id}" if worker.track_id is not None else f"W:{worker.worker_index}"
            label = (
                f"{worker_id} {worker.status} "
                f"H:{'Y' if worker.helmet_detected else 'N'} "
                f"V:{'Y' if worker.vest_detected else 'N'}"
            )

            y_text = max(20, y1 - 10)
            cv2.putText(
                annotated,
                label,
                (x1, y_text),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )

            if worker.violations:
                reason = ", ".join(worker.violations)
                cv2.putText(
                    annotated,
                    reason,
                    (x1, min(y2 + 20, frame.shape[0] - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    color,
                    1,
                    cv2.LINE_AA,
                )

        return annotated

    def _write_json(self, data: Dict, output_path: Path) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def process_image(self, image_path: str, output_dir: str) -> Dict[str, str]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        frame = cv2.imread(str(image_path))
        if frame is None:
            raise ValueError(f"Could not read image: {image_path}")

        workers, scene_status, summary = self.analyze_frame(frame)
        annotated = self.annotate_frame(frame, workers, scene_status)

        image_name = Path(image_path).stem
        annotated_path = output_dir / f"{image_name}_annotated.jpg"
        report_path = output_dir / f"{image_name}_report.json"

        cv2.imwrite(str(annotated_path), annotated)

        report = FrameReport(
            frame_index=0,
            scene_status=scene_status,
            worker_reports=workers,
            summary=summary,
        )
        self._write_json(report.to_dict(), report_path)

        return {
            "annotated_image": str(annotated_path),
            "report_json": str(report_path),
            "scene_status": scene_status,
        }

    def process_video(self, video_path: str, output_dir: str) -> Dict[str, str]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 25.0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        video_name = Path(video_path).stem
        annotated_video_path = output_dir / f"{video_name}_annotated.mp4"
        report_path = output_dir / f"{video_name}_report.json"

        writer = cv2.VideoWriter(
            str(annotated_video_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )

        self.reset_tracking()
        frame_index = 0
        all_reports = []

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            workers, scene_status, summary = self.analyze_frame(
                frame, use_tracking=self.use_tracking,
            )
            annotated = self.annotate_frame(frame, workers, scene_status)
            writer.write(annotated)

            frame_report = FrameReport(
                frame_index=frame_index,
                scene_status=scene_status,
                worker_reports=workers,
                summary=summary,
            )
            all_reports.append(frame_report.to_dict())
            frame_index += 1

        cap.release()
        writer.release()

        final_report = {
            "source_video": str(video_path),
            "total_frames": frame_index,
            "frames": all_reports,
        }
        self._write_json(final_report, report_path)

        return {
            "annotated_video": str(annotated_video_path),
            "report_json": str(report_path),
            "total_frames": str(frame_index),
        }