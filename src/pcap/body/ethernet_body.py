from pcap.body.pcap_body import PcapBody
# Ethernet link type pcap body. UDP 패킷 / TCP 패킷 본문 파싱.
# 구조: [14B Ethernet header] [20B IPv4 header] [8B UDP header or 20B TCP header] [payload]
class UdpEthernetBody(PcapBody):
    ETHERNET_HEADER_LEN = 14
    IPV4_HEADER_LEN = 20
    UDP_HEADER_LEN = 8

    def parser_pcap(self, data: bytes | memoryview) -> None:
        self.original = data

        # source_port: ethernet(14) + ipv4(20) → bytes [34:36]
        eth_end = self.ETHERNET_HEADER_LEN
        ipv4_end = eth_end + self.IPV4_HEADER_LEN
        udp_end = ipv4_end + self.UDP_HEADER_LEN

        self.source_port = int.from_bytes(data[ipv4_end : ipv4_end + 2], "big")
        self.dest_port = int.from_bytes(data[ipv4_end + 2 : ipv4_end + 4], "big")
        # UDP의 경우 seq num 개념이 없으므로 source_port 기반 dummy로 두거나 0
        self.seqNum = 0
        self.dataLoad = data[udp_end:]

class TcpEthernetBody(PcapBody):
    ETHERNET_HEADER_LEN = 14
    IPV4_HEADER_LEN = 20
    TCP_HEADER_FIXED_LEN = 20  # 기본 길이 (option 제외)

    def parser_pcap(self, data: bytes | memoryview) -> None:
        self.original = data

        eth_end = self.ETHERNET_HEADER_LEN
        ipv4_end = eth_end + self.IPV4_HEADER_LEN
        tcp_end = ipv4_end + self.TCP_HEADER_FIXED_LEN

        self.source_port = int.from_bytes(data[ipv4_end : ipv4_end + 2], "big")
        self.dest_port = int.from_bytes(data[ipv4_end + 2 : ipv4_end + 4], "big")
        self.seqNum = int.from_bytes(data[ipv4_end + 4 : ipv4_end + 8], "big")
        self.dataLoad = data[tcp_end:]
