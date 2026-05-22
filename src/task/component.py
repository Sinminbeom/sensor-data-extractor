from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


class Component(ABC):

    @abstractmethod
    def iter_jobs(self) -> Iterable[str]: ...

    @abstractmethod
    def enqueued_count(self) -> int: ...

    @abstractmethod
    def completed_count(self) -> int: ...

    @abstractmethod
    def clear(self) -> None: ...

    def is_complete(self) -> bool:
        enqueued = self.enqueued_count()
        return enqueued == 0 or enqueued == self.completed_count()
