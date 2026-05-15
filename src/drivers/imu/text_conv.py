import threading
# from Drivers.IMU.imu_converter import IMUConverter  # type: ignore
# IMU 메시지 디코더. Thread 베이스지만 run() 안에서 converter.start()만 호출하고 끝남
# (converter가 자체 blocking이므로 .join() 호출 시까지 thread는 동작).
class ImuTextConv(threading.Thread):
    def __init__(self, params: dict) -> None:
        super().__init__()
        self._event = threading.Event()
        # self._converter = IMUConverter(params)  # type: ignore
        self._converter = None  # TODO native module 빌드 후 주입

    def run(self) -> None:
        self._converter.start()
