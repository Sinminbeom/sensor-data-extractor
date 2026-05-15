from pcap.body.pcap_body import PcapBody
from pcap.header.file_header import PcapFileHeader
from pcap.header.packet_header import PcapPacketHeader
# 단일 pcap record (header + body) 묶음. extractor가 element 단위로 azimuth/sequence 등을 조회.
class PcapElementDto:
    def __init__(
        self,
        no: int,
        parent_filename: str,
        file_header: PcapFileHeader,
        packet_header: PcapPacketHeader,
        body: PcapBody,
    ) -> None:
        self.no = no
        self.parent_filename = parent_filename
        self.pcap_file_header = file_header
        self.pcap_packet_header = packet_header
        self.pcap_body = body
        self.payload = body.get_data_load()
    def get_no(self) -> int:
        return self.no

    def get_pcap_file_header(self) -> PcapFileHeader:
        return self.pcap_file_header

    def get_pcap_packet_header(self) -> PcapPacketHeader:
        return self.pcap_packet_header

    def get_pcap_body(self) -> PcapBody:
        return self.pcap_body

    def get_payload(self):
        return self.payload

    def get_payload_pretty(self, clazz):
        payload = clazz()
        payload.parse(self.payload)
        return payload

    def get_packet(self) -> bytes:
        return self.pcap_packet_header.get_original() + bytes(self.pcap_body.get_original())

    def get_parent_filename(self) -> str:
        return self.parent_filename
