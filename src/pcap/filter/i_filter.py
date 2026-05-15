from abc import ABC, abstractmethod

from pcap.sensor.payload_base import PayloadBase
# pcap reader가 packet을 buffer에 넣기 전 filter pass 여부 판단.
class IFilter(ABC):
    @abstractmethod
    def filter_packet(self, parsed: PayloadBase) -> bool: ...
    @abstractmethod
    def invoke(self, payload_bytes) -> bool: ...

class abFilter(IFilter):

    def __init__(self, payload_class: type[PayloadBase]) -> None:
        self._payload_class_type = payload_class
        self._payload_instance = payload_class()

    def invoke(self, payload_bytes) -> bool:
        self._payload_instance.parse(payload_bytes)
        return self.filter_packet(self._payload_instance)
