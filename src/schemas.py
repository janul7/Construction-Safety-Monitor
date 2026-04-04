from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

BBox = Tuple[float, float, float, float]


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    box: BBox
    track_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkerAssessment:
    worker_index: int
    track_id: Optional[int]
    person_box: BBox
    person_confidence: float
    zone_name: str
    required_ppe: List[str]

    helmet_detected: bool
    vest_detected: bool
    helmet_confidence: Optional[float] = None
    vest_confidence: Optional[float] = None

    status: str = "COMPLIANT"  # COMPLIANT | VIOLATION | UNCERTAIN
    violations: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FrameReport:
    frame_index: int
    scene_status: str  # SAFE | UNSAFE | REVIEW
    worker_reports: List[WorkerAssessment]
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "scene_status": self.scene_status,
            "worker_reports": [worker.to_dict() for worker in self.worker_reports],
            "summary": self.summary,
        }