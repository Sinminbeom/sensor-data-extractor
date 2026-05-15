from __future__ import annotations

from collections import deque
from typing import Iterable

from protocol.job_packet import JobPacket
from task.component import Component


class JobBatch(Component):
    """Composite 트리의 Leaf — (vehicle_id, sensor) 단위 잡 묶음.

    enqueued 는 추가 후 비우지 않고, completed 는 잡 완료마다 누적해
    enqueued/completed 비교로 진행률 판단.
    """

    def __init__(self) -> None:
        self._enqueued: deque[JobPacket] = deque()
        self._completed: deque[str] = deque()

    def add(self, job_packet: JobPacket) -> None:
        self._enqueued.append(job_packet)

    def complete(self, pcap_file: str) -> None:
        self._completed.append(pcap_file)

    def iter_jobs(self) -> Iterable[JobPacket]:
        return iter(self._enqueued)

    def enqueued_count(self) -> int:
        return len(self._enqueued)

    def completed_count(self) -> int:
        return len(self._completed)

    def clear(self) -> None:
        self._enqueued.clear()
        self._completed.clear()
