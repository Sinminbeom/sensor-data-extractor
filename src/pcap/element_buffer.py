from __future__ import annotations

from typing import Callable, List, Tuple

from pcap.cursor import PcapCursor, PickCursor
from pcap.element_dto import PcapElementDto
from pcap.file_index import PcapFileIndex
from pcap.sensor.bpearl_payload import BpearlPayloadData
# pcap element list + cursor + file index + pick marking. extractor가 가장 자주 다루는 객체.
class PcapElementBuffer:
    def __init__(self, file_path: str, pcap_elements: list[PcapElementDto] | None = None) -> None:
        self._cursor = PcapCursor()
        self._pick_flag = PickCursor()
        self._file_path = file_path

        if not pcap_elements:
            self.pcapElements: list[PcapElementDto] = []
        else:
            self.pcapElements = pcap_elements
            self._cursor.set_end(len(pcap_elements) - 1)

        self.indexRecord = PcapFileIndex(
            self._file_path, self._cursor.get_start(), self._cursor.get_end()
        )

    # --- single element append ---

    def _check_original_only(self) -> None:
        if len(self.indexRecord.get_file_record()) > 1:
            raise AttributeError()

    def append_element(self, element: PcapElementDto) -> None:
        self._check_original_only()
        self.pcapElements.append(element)
        self._cursor.seek_end(1)
        self.indexRecord.add_original_indexes(1)

    def append_element_left(self, element: PcapElementDto) -> None:
        self._check_original_only()
        self.pcapElements = [element] + self.pcapElements
        self._cursor.seek_current(1)
        self._cursor.seek_end(1)
        self.indexRecord.add_original_indexes(1)

    def append_element_bulk(self, elements: List[PcapElementDto]) -> None:
        self._check_original_only()
        self.pcapElements.extend(elements)
        self._cursor.seek_end(len(elements))
        self.indexRecord.add_original_indexes(len(elements))

    def append_element_left_bulk(self, elements: List[PcapElementDto]) -> None:
        self._check_original_only()
        self.pcapElements = list(elements) + self.pcapElements
        self._cursor.seek_current(len(elements))
        self._cursor.seek_end(len(elements))
        self.indexRecord.add_original_indexes(len(elements))

    # --- multi merge (앞/뒤 file 단위) ---

    def merge(self, file_path: str, elements: list[PcapElementDto]) -> None:
        self.pcapElements.extend(elements)
        self._cursor.seek_end(len(elements))
        self.indexRecord.append(file_path, len(elements))

    def merge_left(self, file_path: str, elements: list[PcapElementDto]) -> None:
        self._cursor.seek_current(len(elements))
        self._cursor.seek_end(len(elements))
        self.indexRecord.append_left(file_path, len(elements))
        self.pcapElements = list(elements) + self.pcapElements

    def merge_buffer(self, other: "PcapElementBuffer | None") -> None:
        if other is None:
            return
        self.merge(other.get_file_path(), other.get_pcap_elements())

    def merge_buffer_left(self, other: "PcapElementBuffer | None") -> None:
        if other is None:
            return
        self.merge_left(other.get_file_path(), other.get_pcap_elements())

    # --- cursor control ---

    def set_start_cursor(self, index: int) -> None:
        self._cursor.set_start(index)

    def set_current_cursor(self, index: int) -> None:
        self._cursor.set_current(index)

    def set_end_cursor(self, index: int) -> None:
        self._cursor.set_end(index)

    def get_start_cursor(self) -> int:
        return self._cursor.get_start()

    def get_current_cursor(self) -> int:
        return self._cursor.get_current()

    def get_end_cursor(self) -> int:
        return self._cursor.get_end()

    def start_marking(self, index: int) -> None:
        self._pick_flag.set_start(index)

    def end_marking(self, index: int) -> None:
        self._pick_flag.set_end(index)

    def get_start_marking(self) -> int:
        return self._pick_flag.get_start()

    def get_end_marking(self) -> int:
        return self._pick_flag.get_end()

    def pick(self) -> "PcapElementBuffer":
        if self._pick_flag.get_start() > self._pick_flag.get_end():
            raise ValueError(
                f"start Mark Index : {self._pick_flag.get_start()}  "
                f"End Mark Index : {self._pick_flag.get_end()}"
            )
        picked = self.pcapElements[self._pick_flag.get_start() : self._pick_flag.get_end() + 1]
        return PcapElementBuffer(self._file_path, picked)

    def pick_with_range(self, start: int, end: int) -> "PcapElementBuffer":
        return PcapElementBuffer(self._file_path, self.pcapElements[start:end])

    # --- read ---

    def _read(self, index: int) -> list[PcapElementDto]:
        if index < 0:
            result = self.pcapElements[
                self._cursor.get_current() + index + 1 : self._cursor.get_current() + 1
            ]
        else:
            result = self.pcapElements[
                self._cursor.get_current() : self._cursor.get_current() + index
            ]
        self.seek(self._cursor.get_current() + index)
        return result

    def next_element(self) -> PcapElementDto | None:
        if self._cursor.get_current() == self._cursor.get_end():
            return None
        return self._read(1)[0]

    def previous_element(self) -> PcapElementDto | None:
        if self._cursor.get_current() == self._cursor.get_start():
            return None
        return self._read(-1)[0]

    def seek(self, index: int) -> None:
        self._cursor.set_current(index)

    def return_to_origin(self) -> None:
        self._cursor.set_current(self.indexRecord.get_original_index()[0])

    def get_current_element(self) -> PcapElementDto:
        return self.pcapElements[self._cursor.get_current()]

    def get_file_path(self) -> str:
        return self._file_path

    def set_file_path(self, path: str) -> None:
        self._file_path = path

    def get_pcap_elements(self) -> list[PcapElementDto]:
        return self.pcapElements

    def get_element(self, index: int) -> PcapElementDto:
        return self.pcapElements[index]

    # --- verification / comparison helpers ---

    def verify_with_func(
        self,
        verify_func: Callable[[PcapElementDto], bool],
        iter_reverse: bool = False,
    ) -> int:
        return self.verify_range_with_func(0, len(self.pcapElements), verify_func, iter_reverse)

    def verify_second_with_func(
        self,
        second: int,
        verify_func: Callable[[PcapElementDto], bool],
        iter_reverse: bool = False,
    ) -> int:
        if second < 0:
            start, end = self.indexRecord.search_before_file_indexes(-second)
        elif second > 0:
            start, end = self.indexRecord.search_after_file_indexes(second)
        else:
            start, end = self.indexRecord.get_original_index()
        return self.verify_range_with_func(start, end, verify_func, iter_reverse)

    def verify_range_with_func(
        self,
        start: int,
        end: int,
        verify_func: Callable[[PcapElementDto], bool],
        iter_reverse: bool = False,
    ) -> int:
        if not iter_reverse:
            for idx in range(start, end):
                if verify_func(self.pcapElements[idx]):
                    return idx
        else:
            for idx in range(end - 1, start - 1, -1):
                if verify_func(self.pcapElements[idx]):
                    return idx
        return -1

    def verify_second_with_func2(
        self,
        second: int,
        verify_func: Callable[[PcapElementDto], Tuple[bool, int]],
        iter_reverse: bool = False,
    ) -> Tuple[int, int]:
        if second < 0:
            start, end = self.indexRecord.search_before_file_indexes(-second)
        elif second > 0:
            start, end = self.indexRecord.search_after_file_indexes(second)
        else:
            start, end = self.indexRecord.get_original_index()
        return self.verify_range_with_func2(start, end, verify_func, iter_reverse)

    def verify_range_with_func2(
        self,
        start: int,
        end: int,
        verify_func: Callable[[PcapElementDto], Tuple[bool, int]],
        iter_reverse: bool = False,
    ) -> Tuple[int, int]:
        if not iter_reverse:
            for idx in range(start, end):
                ok, byte_idx = verify_func(self.pcapElements[idx])
                if ok:
                    return idx, byte_idx
        else:
            for idx in range(end - 1, start - 1, -1):
                ok, byte_idx = verify_func(self.pcapElements[idx])
                if ok:
                    return idx, byte_idx
        return -1, -1

    def compare_with_func(
        self,
        comparison_element: PcapElementDto,
        verify_func: Callable[[PcapElementDto, PcapElementDto], bool],
        iter_reverse: bool = False,
    ) -> int:
        return self.compare_range_with_func(
            0, len(self.pcapElements), comparison_element, verify_func, iter_reverse
        )

    def compare_adjacency_with_func(
        self,
        verify_func: Callable[[PcapElementDto, PcapElementDto], bool],
        iter_reverse: bool = False,
    ) -> int:
        return self.compare_range_adjacency_with_func(
            0, len(self.pcapElements), verify_func, iter_reverse
        )

    def compare_range_with_func(
        self,
        start: int,
        end: int,
        comparison_element: PcapElementDto,
        verify_func: Callable[[PcapElementDto, PcapElementDto], bool],
        iter_reverse: bool = False,
    ) -> int:
        if not iter_reverse:
            for idx in range(start, end):
                if verify_func(comparison_element, self.pcapElements[idx]):
                    return idx
        else:
            for idx in range(end - 1, start - 1, -1):
                if verify_func(comparison_element, self.pcapElements[idx]):
                    return idx
        return -1

    def compare_range_adjacency_with_func(
        self,
        start: int,
        end: int,
        verify_func: Callable[[PcapElementDto, PcapElementDto], bool],
        iter_reverse: bool = False,
    ) -> int:
        if not iter_reverse:
            for idx in range(start, end - 1):
                if verify_func(self.pcapElements[idx], self.pcapElements[idx + 1]):
                    return idx
        else:
            for idx in range(end - 1, start - 1, -1):
                if verify_func(self.pcapElements[idx], self.pcapElements[idx + 1]):
                    return idx
        return -1

    def compare_range_adjacency_with_func2(
        self,
        start: int,
        end: int,
        verify_func: Callable[[PcapElementDto, PcapElementDto], bool],
        iter_reverse: bool = False,
    ) -> int:
        before = None
        if not iter_reverse:
            iterator = range(start, end - 1)
        else:
            iterator = range(end - 1, start - 1, -1)

        for idx in iterator:
            target = self.pcapElements[idx]
            compare = self.pcapElements[idx + 1]
            t_payload = target.get_payload_pretty(BpearlPayloadData)
            c_payload = compare.get_payload_pretty(BpearlPayloadData)

            if (
                t_payload.get_packet_name() == BpearlPayloadData.DIFOP
                and c_payload.get_packet_name() == BpearlPayloadData.DIFOP
            ):
                continue

            if t_payload.get_packet_name() == BpearlPayloadData.DIFOP:
                if before is not None and verify_func(before, compare):
                    return idx
                if not iter_reverse:
                    if verify_func(before, compare) if before else False:
                        return idx
                continue

            if c_payload.get_packet_name() == BpearlPayloadData.DIFOP:
                before = target
                continue

            if verify_func(target, compare):
                return idx

        return -1

    def compare_range_adjacency_with_func3(
        self,
        start: int,
        end: int,
        verify_func: Callable[[PcapElementDto], bool],
        iter_reverse: bool = False,
    ) -> int:
        if not iter_reverse:
            for idx in range(start, end - 1):
                if verify_func(self.pcapElements[idx]):
                    return idx
        else:
            for idx in range(end - 1, start - 1, -1):
                if verify_func(self.pcapElements[idx]):
                    return idx
        return -1

    # --- record / index ---

    def get_index_record(self) -> PcapFileIndex:
        return self.indexRecord

    def get_file_record(self) -> list[str]:
        return self.indexRecord.get_file_record()

    def get_original_file_indexes(self) -> list[int]:
        return self.indexRecord.get_original_index()

    def get_all_file_indexes(self) -> list[list[int]]:
        return self.indexRecord.get_file_index_all()

    def get_first_file_last_packet_index(self) -> int:
        return self.indexRecord.get_first_file_last_packet_index()

    # --- save / sort ---

    def save(self, saved_path: str) -> None:
        if not self.pcapElements:
            return
        file_header = self.pcapElements[0].get_pcap_file_header().get_original()
        with open(saved_path, "wb") as f:
            f.write(file_header)
            for element in self.pcapElements:
                f.write(element.get_packet())

    def sort(self) -> None:
        self.pcapElements.sort(key=lambda x: x.get_pcap_body().get_seq_num())
        self.update_timestamp()

    def update_timestamp(self) -> None:
        from decimal import Decimal

        for i in range(0, len(self.pcapElements) - 1):
            start = 0
            out_of_order: list[dict] = []
            if (
                self.pcapElements[i].get_pcap_packet_header().get_timestamp()
                > self.pcapElements[i + 1].get_pcap_packet_header().get_timestamp()
            ):
                end = self.pcapElements[i + 1].get_pcap_packet_header().get_timestamp()
                for j in range(i, -1, -1):
                    if self.pcapElements[j].get_pcap_packet_header().get_timestamp() > end:
                        out_of_order.insert(
                            0,
                            {
                                "idx": j,
                                "value": self.pcapElements[j].get_pcap_packet_header().get_timestamp(),
                            },
                        )
                    else:
                        start = self.pcapElements[j].get_pcap_packet_header().get_timestamp()
                        break

                if not out_of_order:
                    continue
                gap = (end - start) / len(out_of_order)
                for item in out_of_order:
                    start = start + gap
                    value = Decimal(str(start))
                    captime = int(value.quantize(Decimal("1")))
                    caputime = int((value - captime) * Decimal("1e6"))
                    self.pcapElements[item["idx"]].get_pcap_packet_header().set_captime(captime)
                    self.pcapElements[item["idx"]].get_pcap_packet_header().set_caputime(caputime)
