from abc import ABC, abstractmethod
# link type별 (Ethernet / Linux SLL / Linux SLL V2) 본문 파싱 인터페이스를 제공.
class PcapBody(ABC):
    def __init__(self) -> None:
        self.original: bytes | memoryview = b""
        self.dataLoad: bytes | memoryview = b""
        self.seqNum: int = 0
        self.source_port: int = 0
        self.dest_port: int = 0

    @abstractmethod
    def parser_pcap(self, data: bytes | memoryview) -> None: ...

    def get_data_load(self) -> bytes | memoryview:
        return self.dataLoad

    def get_original(self) -> bytes | memoryview:
        return self.original

    def get_seq_num(self) -> int:
        return self.seqNum
