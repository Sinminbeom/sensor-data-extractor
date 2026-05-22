from abc import ABC, abstractmethod
from typing import List
# 차량 LiDAR/Camera driver 통합 인터페이스. ExtractorModule가 on_start/on_stop/get_dst_path_list 호출.
class IDriver(ABC):
    name: str = ""

    @abstractmethod
    def on_start(self, params: dict) -> None: ...

    @abstractmethod
    def on_stop(self) -> None: ...

    @abstractmethod
    def get_dst_path_list(self) -> List[str]: ...
class IHardware(ABC):
    @abstractmethod
    def _register(self, hardware) -> None: ...

    @abstractmethod
    def load(self, hardware: List) -> "IHardware": ...

    @abstractmethod
    def get(self, name: str): ...
