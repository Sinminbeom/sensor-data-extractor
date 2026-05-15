from pcap.body.ethernet_body import TcpEthernetBody, UdpEthernetBody
from pcap.body.linux_sll_body import TcpLinuxSllBody, UdpLinuxSllBody
from pcap.body.linux_sll_v2_body import TcpLinuxSllV2Body, UdpLinuxSllV2Body
from pcap.body.pcap_body import PcapBody
from pcap.header.file_header import PcapFileHeader
from pcap.header.packet_header import PcapPacketHeader
from pcap.link_type import E_LINK_TYPE, E_PROTOCOL
# pcap binary 영역별 factory. file_header 24B + per-packet (header 16B + payload N bytes).
class PcapFactory:
    @staticmethod
    def file_header(byte_data: bytes | memoryview) -> PcapFileHeader:
        header = PcapFileHeader()
        header.magic = bytes(byte_data[:4])
        header.major = int.from_bytes(byte_data[4:6], "little")
        header.minor = int.from_bytes(byte_data[6:8], "little")
        header.gmt_to_local = int.from_bytes(byte_data[8:12], "little")
        header.timestamp = int.from_bytes(byte_data[12:16], "little")
        header.max_caplen = int.from_bytes(byte_data[16:20], "little")
        header.linktype = int.from_bytes(byte_data[20:24], "little")
        return header

    @staticmethod
    def packet_header(byte_data: bytes | memoryview) -> PcapPacketHeader | None:
        if byte_data is None or len(byte_data) == 0:
            return None

        header = PcapPacketHeader()
        header.captime = int.from_bytes(byte_data[0:4], "little")
        header.caputime = int.from_bytes(byte_data[4:8], "little")
        header.caplen = int.from_bytes(byte_data[8:12], "little")
        header.packlen = int.from_bytes(byte_data[12:16], "little")
        return header

    @staticmethod
    def packet_payload(link_type: int, byte_data: bytes | memoryview) -> PcapBody | None:
        # protocol 식별 byte offset이 link type마다 다르다 (ethernet=23, sll=25, sll2=29).
        if byte_data is None or len(byte_data) <= 0:
            return None

        if link_type == E_LINK_TYPE.ETHERNET:
            protocol = int.from_bytes(byte_data[23:24], "little")
            body = UdpEthernetBody() if protocol == E_PROTOCOL.UDP else TcpEthernetBody()
        elif link_type == E_LINK_TYPE.LINUX_SLL:
            protocol = int.from_bytes(byte_data[25:26], "little")
            body = UdpLinuxSllBody() if protocol == E_PROTOCOL.UDP else TcpLinuxSllBody()
        elif link_type == E_LINK_TYPE.LINUX_SLL_V2:
            protocol = int.from_bytes(byte_data[29:30], "little")
            body = UdpLinuxSllV2Body() if protocol == E_PROTOCOL.UDP else TcpLinuxSllV2Body()
        else:
            return None

        body.parser_pcap(byte_data)
        return body
