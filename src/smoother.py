"""Temporal smoothing for video-based violation detection."""

from collections import defaultdict, deque
from typing import List

from src.schemas import WorkerAssessment


class TemporalSmoother:
    def __init__(self, window_size: int, min_violation_votes: int) -> None:
        self.window_size = window_size
        self.min_violation_votes = min_violation_votes
        self.history = defaultdict(lambda: deque(maxlen=self.window_size))

    def update(self, workers: List[WorkerAssessment]) -> List[WorkerAssessment]:
        for worker in workers:
            if worker.track_id is None:
                continue

            vote = 1 if worker.status == "VIOLATION" else 0
            self.history[worker.track_id].append(vote)

            hist = self.history[worker.track_id]
            if len(hist) == hist.maxlen and sum(hist) >= self.min_violation_votes:
                if worker.status != "VIOLATION":
                    worker.status = "VIOLATION"
                    if "persistent_temporal_violation" not in worker.violations:
                        worker.violations.append("persistent_temporal_violation")
                    worker.notes.append("Violation persisted across multiple frames.")

        return workers
