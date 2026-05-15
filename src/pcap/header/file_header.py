# pcap global file header (24 byte) — magic, version, snaplen, linktype.
# 클래스명 cPcapFileHeader → PcapFileHeader. accessor는 호환 위해 camelCase 그대로 유지.
class PcapFileHeader:
    def __init__(self) -> None:
        self.magic: bytes = b""
        self.major: int = 0
        self.minor: int = 0
        self.gmt_to_local: int = 0
        self.timestamp: int = 0
        self.max_caplen: int = 0
        self.linktype: int = 0

    def get_magic(self) -> bytes:
        return self.magic

    def get_major(self) -> int:
        return self.major

    def get_minor(self) -> int:
        return self.minor

    def get_link_type(self) -> int:
        return self.linktype

    def get_original(self) -> bytes:
        return (
            self.magic
            + self.major.to_bytes(2, "little")
            + self.minor.to_bytes(2, "little")
            + self.gmt_to_local.to_bytes(4, "little")
            + self.timestamp.to_bytes(4, "little")
            + self.max_caplen.to_bytes(4, "little")
            + self.linktype.to_bytes(4, "little")
        )
