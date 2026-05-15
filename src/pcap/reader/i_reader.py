from abc import ABC, abstractmethod

from pcap.element_buffer import PcapElementBuffer
from pcap.filter.i_filter import IFilter
class IPcapReader(ABC):
    def __init__(self, filter_lambda: IFilter | None = None) -> None:
        self.filter_lambda = filter_lambda

    def _set_filter(self, filter_lambda: IFilter | None) -> None:
        self.filter_lambda = filter_lambda

    @abstractmethod
    def read_pcap(
        self,
        pcap_file_path: str,
        world_pcap_first_dto=None,
        custom_filter: IFilter | None = None,
    ) -> PcapElementBuffer | None: ...
