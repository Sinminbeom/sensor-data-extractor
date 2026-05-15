# message buffer가 보유한 여러 pcap file의 element index 범위를 추적.
# 예: original file이 [0, 9999], 앞 1초 file이 추가되면 앞쪽 file은 [0, X], original은 [X+1, X+9999].
class PcapFileIndex:
    def __init__(self, file_path: str, start_index: int, end_index: int) -> None:
        self.original_index = 0
        self.record: list[str] = [file_path]
        if start_index == 0 and end_index == 0:
            self.file_indexes: list[list[int]] = [[start_index, -1]]
        else:
            self.file_indexes = [[start_index, end_index]]

    def append(self, file_path: str, length: int) -> None:
        # 다음 pcap file을 뒤에 붙임 — 새 range는 직전 file의 end+1 부터 end+length 까지
        self.record.append(file_path)
        last_end = self.file_indexes[-1][-1]
        self.file_indexes.append([last_end + 1, last_end + length])

    def append_left(self, file_path: str, length: int) -> None:
        # 앞 pcap file을 추가 — 기존 indexes를 length만큼 shift하고 [0, length-1] 추가
        tmp_record = [file_path]
        tmp_record.extend(self.record)

        new_indexes = [[0, length - 1]]
        for cursor in self.file_indexes:
            cursor[0] += length
            cursor[1] += length
        new_indexes.extend(self.file_indexes)

        self.record = tmp_record
        self.file_indexes = new_indexes
        self.original_index += 1

    def get_file_record(self) -> list[str]:
        return self.record

    def add_original_indexes(self, index: int) -> None:
        self.file_indexes[self.original_index][1] += index

    def get_file_index_all(self) -> list[list[int]]:
        return self.file_indexes

    def get_original_index(self) -> list[int]:
        return self.file_indexes[self.original_index]

    def search_before_file_indexes(self, before_cnt: int) -> list[int]:
        if self.original_index - before_cnt < 0:
            raise FileNotFoundError
        return self.file_indexes[self.original_index - before_cnt]

    def search_after_file_indexes(self, after_cnt: int) -> list[int]:
        if self.original_index + after_cnt >= len(self.file_indexes):
            raise FileNotFoundError
        return self.file_indexes[self.original_index + after_cnt]

    def search_before_file_name(self, before_cnt: int) -> str:
        if self.original_index - before_cnt < 0:
            raise FileNotFoundError
        return self.record[self.original_index - before_cnt]

    def search_after_file_name(self, after_cnt: int) -> str:
        if self.original_index + after_cnt >= len(self.file_indexes):
            raise FileNotFoundError
        return self.record[self.original_index + after_cnt]

    def get_before_file_count(self) -> int:
        return self.original_index

    def get_after_file_count(self) -> int:
        return len(self.record) - self.original_index - 1

    def get_first_file_last_packet_index(self) -> int:
        return self.file_indexes[0][-1]
