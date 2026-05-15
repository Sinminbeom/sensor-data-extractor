from abc import ABC
# sensor별 payload parser의 base. parse()는 payload bytes를 받아 instance attribute에 저장.
class PayloadBase(ABC):
    def __init__(self) -> None:
        self.data: bytes | memoryview = b""

    def parse(self, data: bytes | memoryview) -> None:
        self.data = data

    def get_data(self) -> bytes | memoryview:
        return self.data

    def get_original(self) -> bytes | memoryview:
        return self.get_data()
