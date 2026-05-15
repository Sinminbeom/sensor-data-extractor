# pcap record header (16 byte) — timestamp (sec / usec), caplen, packlen.
class PcapPacketHeader:
    def __init__(self) -> None:
        self.captime: int = 0
        self.caputime: int = 0
        self.caplen: int = 0
        self.packlen: int = 0

    def get_packet_len(self) -> int:
        return self.caplen

    def get_timestamp(self) -> float:
        return self.captime + self.caputime / 1_000_000

    def set_captime(self, value: int) -> None:
        self.captime = value

    def set_caputime(self, value: int) -> None:
        self.caputime = value

    def get_original(self) -> bytes:
        return (
            self.captime.to_bytes(4, "little")
            + self.caputime.to_bytes(4, "little")
            + self.caplen.to_bytes(4, "little")
            + self.packlen.to_bytes(4, "little")
        )
