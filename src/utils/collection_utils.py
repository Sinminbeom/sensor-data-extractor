from collections import deque
from itertools import islice
from typing import Callable, TypeVar
# dict-or-deque static helpers. dependency-free static utility 묶음.
K = TypeVar("K")
V = TypeVar("V")

class CollectionUtils:
    @staticmethod
    def deque_slice_deque(target, start: int, end: int) -> deque:
        return deque(islice(target, start, end))

    @staticmethod
    def deque_slice_array(target, start: int, end: int):
        return islice(target, start, end)

    @staticmethod
    def dict_extends(d: dict, key, factory: Callable[[], V]) -> V:
        if key in d:
            return d[key]
        d[key] = factory()
        return d[key]

    @staticmethod
    def dict_get_value(d: dict | None, key):
        if d is None:
            return None
        return d.get(key)
