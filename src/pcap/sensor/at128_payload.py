from pcap.sensor.payload_base import PayloadBase
# AT128 (Hesai) packet payload (1118 byte) parser. azimuth / fineAzimuth / returnMode 추출.
class At128PayloadData(PayloadBase):
    def __init__(self) -> None:
        super().__init__()
        self.azimuth: int | None = None
        self.fineAzimuth: int | None = None
        self.azimuth2: int | None = None
        self.fineAzimuth2: int | None = None
        self.returnMode: int | None = None

    def parse(self, data: bytes | memoryview) -> None:
        super().parse(data)
        if len(self.get_data()) != 1118:
            return
        self.azimuth = int.from_bytes(self.data[12 : 12 + 2], "little")
        self.fineAzimuth = int.from_bytes(self.data[14 : 15], "little")
        self.azimuth2 = int.from_bytes(self.data[527 : 529], "little")
        self.fineAzimuth2 = int.from_bytes(self.data[529 : 530], "little")
        self.returnMode = int.from_bytes(self.data[1070 : 1071], "little")

    def get_azimuth(self) -> int | None:
        return self.azimuth

    def get_fine_azimuth(self) -> int | None:
        return self.fineAzimuth

    def get_azimuth2(self) -> int | None:
        return self.azimuth2

    def get_fine_azimuth2(self) -> int | None:
        return self.fineAzimuth2

    def get_return_mode(self) -> int | None:
        return self.returnMode
