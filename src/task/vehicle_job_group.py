from __future__ import annotations

from typing import Iterable

from protocol.job_packet import JobPacket
from task.component import Component
from task.job_batch import JobBatch


class VehicleJobGroup(Component):
    """Composite — vehicle_id 단위로 JobBatch 묶음을 보관."""

    def __init__(self) -> None:
        self._batches: dict[str, JobBatch] = {}

    # --- Composite child management ---

    def add_batch(self, vehicle_id: str, batch: JobBatch) -> None:
        self._batches[vehicle_id] = batch

    def get_batch(self, vehicle_id: str) -> JobBatch | None:
        return self._batches.get(vehicle_id)

    # --- Component (Composite aggregation) ---

    def iter_jobs(self) -> Iterable[JobPacket]:
        for batch in self._batches.values():
            yield from batch.iter_jobs()

    def enqueued_count(self) -> int:
        return sum(b.enqueued_count() for b in self._batches.values())

    def completed_count(self) -> int:
        return sum(b.completed_count() for b in self._batches.values())

    def clear(self) -> None:
        for b in self._batches.values():
            b.clear()
