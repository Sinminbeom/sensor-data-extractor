import threading
import time
# from Drivers.AT128.at128_converter import At128Converter  # type: ignore
# Thread 베이스 — C++ At128Converter의 start/stop을 wrap. AT128 추출기에서 sleep 폴링으로 isEndSavePcd 확인.
class At128PcdConv(threading.Thread):
    def __init__(self, params: dict) -> None:
        super().__init__()
        self._event = threading.Event()
        # self._converter = At128Converter(params)  # type: ignore
        self._converter = None  # TODO native module 빌드 후 주입

    def run(self) -> None:
        self._converter.start()
        while not self._event.is_set():
            if self._converter.get_is_end_save_pcd():
                self._event.set()
                time.sleep(0.1)

    def get_is_end_save_pcd(self) -> bool:
        return self._converter.get_is_end_save_pcd()

    def stop(self) -> None:
        self._converter.stop()

    def get_dst_path_list(self) -> list[str]:
        return self._converter.get_dst_path_list()
