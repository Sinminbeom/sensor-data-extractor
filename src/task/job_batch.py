from __future__ import annotations

from collections import deque
from typing import Iterable

from task.component import Component


class JobBatch(Component):
    """Composite 트리의 Leaf — (vehicle_id, sensor) 단위 잡 묶음.

    enqueued / completed 모두 job_id 누적. enqueued/completed 갯수 비교로 진행률 판단.
    """

    def __init__(self) -> None:
        self._enqueued: deque[str] = deque()
        self._completed: deque[str] = deque()

    def add(self, job_id: str) -> None:
        self._enqueued.append(job_id)

    def complete(self, pcap_file: str) -> None:
        self._completed.append(pcap_file)

    def iter_jobs(self) -> Iterable[str]:
        return iter(self._enqueued)

    def enqueued_count(self) -> int:
        return len(self._enqueued)

    def completed_count(self) -> int:
        return len(self._completed)

    def clear(self) -> None:
        self._enqueued.clear()
        self._completed.clear()
