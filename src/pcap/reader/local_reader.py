import os.path

from pcap.element_buffer import PcapElementBuffer
from pcap.element_dto import PcapElementDto
from pcap.filter.i_filter import IFilter
from pcap.pcap_factory import PcapFactory
from pcap.reader.i_reader import IPcapReader
# 로컬 파일시스템에서 pcap을 stream으로 읽으며 element를 만들어 buffer에 채움.
class LocalStorageReader(IPcapReader):
    LINK_TYPE_SIZE = 16  # pcap record header 길이

    def __init__(self, filter_lambda: IFilter | None = None) -> None:
        super().__init__(filter_lambda)

    def read_pcap(
        self,
        pcap_file_path: str,
        world_pcap_first_dto=None,
        custom_filter: IFilter | None = None,
    ) -> PcapElementBuffer | None:
        read_filter = custom_filter if custom_filter is not None else self.filter_lambda

        if not os.path.exists(pcap_file_path):
            return None

        container = PcapElementBuffer(pcap_file_path)

        with open(pcap_file_path, "rb") as f:
            file_header = PcapFactory.file_header(f.read(24))
            no = 1
            while True:
                packet_header = PcapFactory.packet_header(f.read(LocalStorageReader.LINK_TYPE_SIZE))
                if packet_header is None:
                    break

                packet_body = PcapFactory.packet_payload(
                    file_header.get_link_type(), f.read(packet_header.get_packet_len())
                )

                if packet_body is None:
                    continue

                if read_filter is not None and not read_filter.invoke(packet_body.get_data_load()):
                    continue

                element = PcapElementDto(no, pcap_file_path, file_header, packet_header, packet_body)
                container.append_element(element)
                no += 1

        return container
