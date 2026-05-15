from python_library.logger.app_logger import AppLogger
from python_library.storage.storage import IStorage

from pcap.element_buffer import PcapElementBuffer
from pcap.element_dto import PcapElementDto
from pcap.filter.i_filter import IFilter
from pcap.pcap_factory import PcapFactory
from pcap.reader.i_reader import IPcapReader
# python-library IStorage 도입 후 storage.read(path)로 binary 전체를 한 번에 받아 memoryview로 stream 처리.
class ObjectStorageReader(IPcapReader):
    LINK_TYPE_SIZE = 16

    def __init__(self, storage: IStorage, filter_lambda: IFilter | None = None) -> None:
        super().__init__(filter_lambda)
        self.storage = storage

    def read_pcap(
        self,
        pcap_file_path: str,
        world_pcap_first_dto=None,
        custom_filter: IFilter | None = None,
    ) -> PcapElementBuffer | None:
        read_filter = custom_filter if custom_filter is not None else self.filter_lambda

        try:
            original_bytes = self.storage.read(pcap_file_path)
        except Exception as e:
            AppLogger.instance().exception(f"Storage read failed: {pcap_file_path} : {e}")
            return None

        container = PcapElementBuffer(pcap_file_path)

        # 24 byte global header → 첫 packet record는 offset 24 부터
        file_header = PcapFactory.file_header(original_bytes[:24])
        packet_start_cursor = 24
        packet_header_end_cursor = packet_start_cursor + ObjectStorageReader.LINK_TYPE_SIZE

        original_view = memoryview(original_bytes)
        no = 1
        while True:
            if packet_start_cursor >= len(original_bytes):
                break

            packet_header = PcapFactory.packet_header(
                original_view[packet_start_cursor:packet_header_end_cursor]
            )
            if packet_header is None:
                break

            payload_view = original_view[
                packet_header_end_cursor : packet_header_end_cursor + packet_header.get_packet_len()
            ]
            packet_body = PcapFactory.packet_payload(file_header.get_link_type(), payload_view)

            advance = packet_header.get_packet_len()
            if packet_body is None:
                packet_start_cursor = packet_header_end_cursor + advance
                packet_header_end_cursor = packet_start_cursor + ObjectStorageReader.LINK_TYPE_SIZE
                continue

            if read_filter is not None and not read_filter.invoke(packet_body.get_data_load()):
                packet_start_cursor = packet_header_end_cursor + advance
                packet_header_end_cursor = packet_start_cursor + ObjectStorageReader.LINK_TYPE_SIZE
                continue

            element = PcapElementDto(no, pcap_file_path, file_header, packet_header, packet_body)
            container.append_element(element)

            packet_start_cursor = packet_header_end_cursor + advance
            packet_header_end_cursor = packet_start_cursor + ObjectStorageReader.LINK_TYPE_SIZE
            no += 1

        return container
