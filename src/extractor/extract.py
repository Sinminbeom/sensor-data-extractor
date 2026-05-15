from abc import ABC, abstractmethod

from extractor.extract_context import ExtractContext


class IExtract(ABC):
    """Sensor 별 추출기 인터페이스.

    각 구현은 (ExtractContext) → None staticmethod 로 제공.
    """

    @staticmethod
    @abstractmethod
    def extract(ctx: ExtractContext) -> None: ...
