# pcap element buffer 내 read cursor (start/current/end).
class PcapCursor:
    def __init__(self) -> None:
        self.start_cursor = 0
        self.current_cursor = 0
        self.end_cursor = 0

    def init(self) -> None:
        self.start_cursor = 0
        self.current_cursor = 0
        self.end_cursor = 0

    def seek_start(self, index: int) -> None:
        self.start_cursor += index

    def seek_current(self, index: int) -> None:
        self.current_cursor += index

    def seek_end(self, index: int) -> None:
        self.end_cursor += index

    def set_start(self, index: int) -> None:
        self.start_cursor = index

    def set_current(self, index: int) -> None:
        self.current_cursor = index

    def set_end(self, index: int) -> None:
        self.end_cursor = index

    def get_start(self) -> int:
        return self.start_cursor

    def get_current(self) -> int:
        return self.current_cursor

    def get_end(self) -> int:
        return self.end_cursor
# pick 범위 marking을 위한 cursor 쌍.
class PickCursor:
    def __init__(self) -> None:
        self.start_pick = 0
        self.end_pick = 0

    def set_start(self, index: int) -> None:
        self.start_pick = index

    def set_end(self, index: int) -> None:
        self.end_pick = index

    def get_start(self) -> int:
        return self.start_pick

    def get_end(self) -> int:
        return self.end_pick
