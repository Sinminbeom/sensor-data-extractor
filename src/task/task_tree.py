from __future__ import annotations

from typing import Iterable

from task.component import Component
from task.job_batch import JobBatch


class TaskTree(Component):
    """Composite root — (date, vehicle_id) 단위 잡 묶음.

    vehicle_id 별 JobBatch 직접 보관 (이전 VehicleJobGroup 중간 layer 제거).
    """

    def __init__(self, date: str, vehicle_id: str) -> None:
        self.date = date
        self.vehicle_id = vehicle_id
        self._batches: dict[str, JobBatch] = {}

    # --- Composite child management ---

    def add_batch(self, vehicle_id: str, batch: JobBatch) -> None:
        self._batches[vehicle_id] = batch

    def get_batch(self, vehicle_id: str) -> JobBatch | None:
        return self._batches.get(vehicle_id)

    def is_populated(self) -> bool:
        return len(self._batches) > 0

    def complete_job(self, vehicle_id: str, pcap_file: str) -> None:
        batch = self._batches.get(vehicle_id)
        if batch is not None:
            batch.complete(pcap_file)

    # --- Component (Composite aggregation) ---

    def iter_jobs(self) -> Iterable[str]:
        for batch in self._batches.values():
            yield from batch.iter_jobs()

    def enqueued_count(self) -> int:
        return sum(b.enqueued_count() for b in self._batches.values())

    def completed_count(self) -> int:
        return sum(b.completed_count() for b in self._batches.values())

    def clear(self) -> None:
        for b in self._batches.values():
            b.clear()
