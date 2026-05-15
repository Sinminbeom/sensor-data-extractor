from pcap.sensor.payload_base import PayloadBase
# RoboSense BPearl 32B packet payload parser. MSOP/DIFOP 두 종류 구분 + MSOP의 경우 azimuth 추출.
class BpearlPayloadData(PayloadBase):
    MSOP = "MSOP"
    DIFOP = "DIFOP"
    # DIFOP 패킷 식별자 (앞 8 byte)
    DIFOP_HEADER = b"\xa5\xff\x00Z\x11\x11UU"

    def __init__(self) -> None:
        super().__init__()
        self.packetName: str | None = None
        self.header: bytes | memoryview | None = None
        self.azimuth: float | None = None

    def parse(self, data: bytes | memoryview) -> None:
        super().parse(data)

        if bytes(self.data[:8]) == BpearlPayloadData.DIFOP_HEADER:
            # DIFOP 패킷은 azimuth/payload 본문 없음 — packetName만 마킹
            self.packetName = BpearlPayloadData.DIFOP
            return

        # MSOP — header 42B + azimuth (big-endian, /100 보정)
        self.packetName = BpearlPayloadData.MSOP
        self.header = self.data[:42]
        self.azimuth = int.from_bytes(self.data[44 : 46], "big") / 100

    def get_packet_name(self) -> str | None:
        return self.packetName

    def get_header(self):
        return self.header

    def get_azimuth(self) -> float | None:
        return self.azimuth
