"""Temporal smoothing for video-based violation detection."""

from collections import defaultdict, deque
from typing import List

from src.schemas import WorkerAssessment


class TemporalSmoother:
    """Sliding-window voter that confirms persistent violations across video frames.

    For each tracked worker, maintains a rolling window of violation votes.
    A worker is flagged as a persistent violation only when the number of
    violation votes within the window meets the minimum threshold.
    This reduces false alarms from single-frame detection errors.
    """

    def __init__(self, window_size: int, min_violation_votes: int) -> None:
        self.window_size = window_size
        self.min_violation_votes = min_violation_votes
        self.history = defaultdict(lambda: deque(maxlen=self.window_size))

    def update(self, workers: List[WorkerAssessment]) -> List[WorkerAssessment]:
        for worker in workers:
            if worker.track_id is None:
                continue

            # Cast a vote: 1 if currently violating, 0 if compliant
            vote = 1 if worker.status == "VIOLATION" else 0
            self.history[worker.track_id].append(vote)

            # Only flag persistent violation once window is full and votes meet threshold
            hist = self.history[worker.track_id]
            if len(hist) == hist.maxlen and sum(hist) >= self.min_violation_votes:
                if worker.status != "VIOLATION":
                    worker.status = "VIOLATION"
                    if "persistent_temporal_violation" not in worker.violations:
                        worker.violations.append("persistent_temporal_violation")
                    worker.notes.append("Violation persisted across multiple frames.")

        return workers
