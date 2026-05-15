from pcap.filter.i_filter import abFilter
from pcap.sensor.payload_base import PayloadBase
# AT128 packet은 payload 길이가 1118 byte인 것만 통과.
class At128Filter(abFilter):
    def filter_packet(self, parsed: PayloadBase) -> bool:
        return len(parsed.get_data()) == 1118
