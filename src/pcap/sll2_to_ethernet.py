from typing import ClassVar, List
# Linux SLL V2 link type pcap → 표준 Ethernet pcap 변환 (driver C++ 모듈이 Ethernet pcap만 받는 경우 사용).
class Sll2ToEthernet:
    PCAP_HEADER_LEN = 24
    TIMESTAMP_LEN = 8
    PACKET_LENGTH_LEN = 8
    SLL2_LINK_HEADER_LEN = 20
    ETHERNET_LINK_HEADER_LEN = 14
    IPV4_HEADER_LEN = 20
    UDP_HEADER_LEN = 8

    # subclass에서 sensor별 payload 길이 지정
    payload_length: ClassVar[int] = 0

    def __init__(self) -> None:
        self.data: List[bytes] = []
        self.bytes_data: bytes = b""
        self.cnt: int = 0

    def clear(self) -> None:
        self.data.clear()
        self.cnt = 0

    def convert(self, input_path: str, output_path: str) -> None:
        self._read_sll2(input_path)
        self._concat_to_bytes()
        self._write_ethernet(output_path)

    def _read_sll2(self, input_path: str) -> None:
        # 각 record의 SLL2 link header(20B)를 Ethernet header(14B)로 치환.
        with open(input_path, "rb") as f:
            pcap_header = f.read(self.PCAP_HEADER_LEN)
            self.data.append(pcap_header[:20])
            # link type 수정: SLL2 → Ethernet (1)
            self.data.append(b"\x01\x00\x00\x00")

            while True:
                timestamp = f.read(self.TIMESTAMP_LEN)
                if timestamp == b"":
                    break
                self.data.append(timestamp)

                packet_length_bytes = f.read(self.PACKET_LENGTH_LEN)
                packet_length = int.from_bytes(packet_length_bytes[:4], byteorder="little")
                # SLL2 → Ethernet 변환 시 link header가 20B → 14B 이므로 6B 감소
                packet_length = packet_length - 6
                new_length_bytes = packet_length.to_bytes(4, byteorder="little")
                new_length_bytes += new_length_bytes  # caplen + packlen 둘 다 동일
                self.data.append(new_length_bytes)

                # SLL2 header → Ethernet header (dest 6B + src 6B + type 2B)
                sll2_header = f.read(self.SLL2_LINK_HEADER_LEN)
                destination = b"\x00\x00\x00\x00\x01\x03"
                source = sll2_header[12:18]
                ether_type = sll2_header[:2]

                self.data.append(destination)
                self.data.append(source)
                self.data.append(ether_type)

                self.data.append(f.read(self.IPV4_HEADER_LEN))
                self.data.append(f.read(self.UDP_HEADER_LEN))
                self.data.append(f.read(self.payload_length))

                self.cnt += 1

    def _concat_to_bytes(self) -> None:
        self.bytes_data = b"".join(self.data)

    def _write_ethernet(self, output_path: str) -> None:
        with open(output_path, "wb") as f:
            f.write(self.bytes_data)

# AT128 payload 길이 1118 byte
class At128EthernetConvert(Sll2ToEthernet):
    payload_length = 1118

# RSBP payload 길이 1248 byte
class RsbpEthernetConvert(Sll2ToEthernet):
    payload_length = 1248
