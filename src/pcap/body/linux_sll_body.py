from pcap.body.pcap_body import PcapBody
# Linux SLL (cooked-mode) link type pcap body. SLL header(16B) + IPv4(20B) + UDP/TCP header + payload.
class UdpLinuxSllBody(PcapBody):
    SLL_HEADER_LEN = 16
    IPV4_HEADER_LEN = 20
    UDP_HEADER_LEN = 8

    def parser_pcap(self, data: bytes | memoryview) -> None:
        self.original = data

        sll_end = self.SLL_HEADER_LEN
        ipv4_end = sll_end + self.IPV4_HEADER_LEN
        udp_end = ipv4_end + self.UDP_HEADER_LEN

        self.source_port = int.from_bytes(data[ipv4_end : ipv4_end + 2], "big")
        self.dest_port = int.from_bytes(data[ipv4_end + 2 : ipv4_end + 4], "big")
        self.seqNum = 0
        self.dataLoad = data[udp_end:]

class TcpLinuxSllBody(PcapBody):
    SLL_HEADER_LEN = 16
    IPV4_HEADER_LEN = 20
    TCP_HEADER_FIXED_LEN = 20

    def parser_pcap(self, data: bytes | memoryview) -> None:
        self.original = data

        sll_end = self.SLL_HEADER_LEN
        ipv4_end = sll_end + self.IPV4_HEADER_LEN
        tcp_end = ipv4_end + self.TCP_HEADER_FIXED_LEN

        self.source_port = int.from_bytes(data[ipv4_end : ipv4_end + 2], "big")
        self.dest_port = int.from_bytes(data[ipv4_end + 2 : ipv4_end + 4], "big")
        self.seqNum = int.from_bytes(data[ipv4_end + 4 : ipv4_end + 8], "big")
        self.dataLoad = data[tcp_end:]
