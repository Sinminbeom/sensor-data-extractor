import threading
import time
# from Drivers.RSBP.rsbp_converter import RSBPConverter  # type: ignore
# AT128PcdConv와 비슷한 구조지만 callback 등록(register_callback) 기능이 추가됨.
class RsbpPcdConv(threading.Thread):
    def __init__(self, params: dict) -> None:
        super().__init__()
        self._event = threading.Event()
        # self._converter = RSBPConverter(params)  # type: ignore
        self._converter = None  # TODO native module 빌드 후 주입

    def run(self) -> None:
        self._converter.start()
        while not self._event.is_set():
            time.sleep(0.1)

    def stop(self) -> None:
        self._converter.stop()
        self._event.set()

    def get_dst_path_list(self) -> list[str]:
        return self._converter.get_dst_path_list()

    def register_callback(self) -> None:
        self._converter.register_callback(self.stop)
