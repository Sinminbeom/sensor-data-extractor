from __future__ import annotations

import os

from python_library.storage.storage import IStorage

from pcap.element_buffer import PcapElementBuffer
from pcap.filter.i_filter import IFilter
from pcap.reader.local_reader import LocalStorageReader
from pcap.reader.object_storage_reader import ObjectStorageReader
from utils.time_string_fit import E_CALENDAR_TYPE, TimeStringFit, TimeStringInterval
# 대상 pcap 1개 + 앞/뒤 N초 pcap을 묶어 단일 element buffer로 노출.
# 파일명 패턴: <sensor>_<YYYYMMDDHHMMSS>.pcap, 경로 패턴: <route>/<YYYYMMDD>/<HH>/<MM>/<file>
class PcapMessageBuffer:
    def __init__(
        self,
        storage: IStorage | None,
        file_path: str,
        filter_obj: IFilter | None = None,
    ) -> None:
        self.storage = storage

        if storage is not None:
            # python-library IStorage 기반 — connect는 builder가 이미 호출했으므로 idempotent하게 한 번 더 호출
            try:
                storage.connect()
            except Exception:
                pass
            self._reader = ObjectStorageReader(storage, filter_obj)
        else:
            # storage가 None이면 fs 직접 접근 (legacy 호환)
            self._reader = LocalStorageReader(filter_obj)

        self.filepath = file_path
        self.filter = filter_obj
        self._buffer: PcapElementBuffer | None = self._reader.read_pcap(self.filepath)

        self._base_filename = self._compute_base_filename()
        self._base_file_route = self._compute_base_file_route()
        self._base_file_date = self._compute_base_file_date()
        self._base_file_sensor_name = self._compute_base_file_sensor_name()

        self._before_file_date = self._base_file_date
        self._after_file_date = self._base_file_date

    def sort(self) -> None:
        if self._buffer is not None:
            self._buffer.sort()

    # --- read controls ---

    def next_element(self, auto_read: bool = False):
        nxt = self._buffer.next_element()
        if nxt is not None:
            return nxt
        if not auto_read:
            return None
        before = len(self._buffer.get_all_file_indexes())
        self.read_next_file()
        if len(self._buffer.get_all_file_indexes()) == before:
            return None
        return self._buffer.next_element()

    def previous_element(self, auto_read: bool = False):
        prev = self._buffer.previous_element()
        if prev is not None:
            return prev
        if not auto_read:
            return None
        before = len(self._buffer.get_all_file_indexes())
        self.read_previous_file()
        if len(self._buffer.get_all_file_indexes()) == before:
            return None
        return self._buffer.previous_element()

    def seek(self, index: int) -> None:
        self._buffer.seek(index)

    # --- read previous / next file ---

    def read_previous_file(self, filter_obj: IFilter | None = None) -> None:
        self.read_previous_file_until(filter_obj=filter_obj)

    def read_previous_file_until(self, sec: int = 1, filter_obj: IFilter | None = None) -> None:
        if sec == 0:
            raise ValueError("[ERROR] unacceptable argument -> 0")

        calculator = TimeStringFit()
        calculator.set(self._before_file_date)
        calculator.next_element(E_CALENDAR_TYPE.SEC, -sec)

        next_time = calculator.get()
        tmp_times: list[str] = []
        TimeStringFit().coroutine(
            next_time,
            self._before_file_date,
            TimeStringInterval(E_CALENDAR_TYPE.SEC, 1),
            lambda tsf: tmp_times.append(tsf.get()),
            "<",
        )
        tmp_times.reverse()

        cursor_time = ""
        for read_time in tmp_times:
            try:
                new_path = self._make_pcap_path(read_time)
                merged = self._reader.read_pcap(new_path, custom_filter=filter_obj)
                if merged is None:
                    continue
                self._buffer.merge_buffer_left(merged)
                cursor_time = read_time
            except Exception:
                continue

        if cursor_time != "":
            self._before_file_date = cursor_time

    def read_next_file(self, filter_obj: IFilter | None = None) -> None:
        self.read_next_file_until(filter_obj=filter_obj)

    def read_next_file_until(self, sec: int = 1, filter_obj: IFilter | None = None) -> None:
        if sec == 0:
            raise ValueError("[ERROR] unacceptable argument -> 0")

        calculator = TimeStringFit()
        calculator.set(self._after_file_date)
        calculator.next_element(E_CALENDAR_TYPE.SEC, sec)

        next_time = calculator.get()
        tmp_times: list[str] = []
        TimeStringFit().coroutine(
            next_time,
            self._after_file_date,
            TimeStringInterval(E_CALENDAR_TYPE.SEC, -1),
            lambda tsf: tmp_times.append(tsf.get()),
            ">",
        )
        tmp_times.reverse()

        cursor_time = ""
        for read_time in tmp_times:
            try:
                new_path = self._make_pcap_path(read_time)
                merged = self._reader.read_pcap(new_path, custom_filter=filter_obj)
                if merged is None:
                    continue
                self._buffer.merge_buffer(merged)
                cursor_time = read_time
            except Exception:
                continue

        if cursor_time != "":
            self._after_file_date = cursor_time

    # --- accessors ---

    def get_before_file_count(self) -> int:
        return self._buffer.get_index_record().get_before_file_count()

    def get_after_file_count(self) -> int:
        return self._buffer.get_index_record().get_after_file_count()

    def get_buffer(self) -> PcapElementBuffer:
        return self._buffer

    def get_current_element(self):
        return self._buffer.get_current_element()

    def get_storage(self):
        return self.storage

    def get_filepath(self) -> str:
        return self.filepath

    # --- helpers ---

    def _make_pcap_path(self, time_str: str) -> str:
        # IStorage 추상화 사용 후 모든 경로는 POSIX "/" delimiter로 통일 (Windows 분기 제거).
        delim = "/"
        return (
            self._base_file_route + time_str[:8] + delim
            + time_str[8:10] + delim
            + time_str[10:12] + delim
            + self._base_file_sensor_name + "_" + time_str + ".pcap"
        )

    def _compute_base_filename(self) -> str:
        return os.path.basename(self.filepath)

    def _compute_base_file_route(self) -> str:
        base = self._compute_base_filename()
        yyyymmdd = base.split(".")[0].split("_")[-1][:8]
        return self.filepath.split(yyyymmdd)[0]

    def _compute_base_file_date(self) -> str:
        return self._compute_base_filename().split(".")[0].split("_")[-1]

    def _compute_base_file_sensor_name(self) -> str:
        base = self._compute_base_filename()
        tmp = base.split(".")[0]
        yyyymmdd = tmp.split("_")[-1]
        return tmp.replace("_" + yyyymmdd, "")
