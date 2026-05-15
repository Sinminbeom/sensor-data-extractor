from __future__ import annotations

from typing import Iterable

from protocol.job_packet import JobPacket
from task.component import Component
from task.vehicle_job_group import VehicleJobGroup


class TaskTree(Component):
    """Composite root — 단일 date 단위로 VehicleJobGroup 하나를 보관.

    구조상 (date → VehicleJobGroup) 매핑이 가능하지만 실 사용은 date 1개 고정이라
    degenerate 형태로 평탄화. multi-date 가 필요해지면 dict 로 확장.
    """

    def __init__(self, date: str, vehicle_id: str) -> None:
        self.date = date
        self.vehicle_id = vehicle_id
        self._vehicle_jobs: VehicleJobGroup | None = None

    # --- Composite child management ---

    def set_vehicle_jobs(self, group: VehicleJobGroup) -> None:
        self._vehicle_jobs = group

    def is_populated(self) -> bool:
        return self._vehicle_jobs is not None

    def complete_job(self, vehicle_id: str, pcap_file: str) -> None:
        if self._vehicle_jobs is None:
            return
        batch = self._vehicle_jobs.get_batch(vehicle_id)
        if batch is not None:
            batch.complete(pcap_file)

    # --- Component (Composite aggregation) ---

    def iter_jobs(self) -> Iterable[JobPacket]:
        if self._vehicle_jobs is None:
            return iter(())
        return self._vehicle_jobs.iter_jobs()

    def enqueued_count(self) -> int:
        if self._vehicle_jobs is None:
            return 0
        return self._vehicle_jobs.enqueued_count()

    def completed_count(self) -> int:
        if self._vehicle_jobs is None:
            return 0
        return self._vehicle_jobs.completed_count()

    def clear(self) -> None:
        if self._vehicle_jobs is not None:
            self._vehicle_jobs.clear()
