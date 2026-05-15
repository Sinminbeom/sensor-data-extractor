from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from protocol.job_packet import JobPacket


class Component(ABC):

    @abstractmethod
    def iter_jobs(self) -> Iterable[JobPacket]: ...

    @abstractmethod
    def enqueued_count(self) -> int: ...

    @abstractmethod
    def completed_count(self) -> int: ...

    @abstractmethod
    def clear(self) -> None: ...

    def is_complete(self) -> bool:
        enqueued = self.enqueued_count()
        return enqueued == 0 or enqueued == self.completed_count()
