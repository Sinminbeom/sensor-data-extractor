from pcap.filter.i_filter import abFilter
from pcap.sensor.payload_base import PayloadBase
class BpearlFilter(abFilter):
    def filter_packet(self, parsed: PayloadBase) -> bool:
        return True
