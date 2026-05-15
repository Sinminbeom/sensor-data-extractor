import math

from drivers.driver import IDriver
from drivers.rsbp.pcd_conv import RsbpPcdConv
# RSBP 차량 driver. extrinsic 변환 helper (_conv_ap500_extrinsic)가 포함되어 있음.
class Rsbp(IDriver):
    name: str = "RSBP"

    src_ip: str = "localhost"
    protocol: str = "udp"
    dst_ip: str = "localhost"
    dst_port: int = -1
    difop_port: int = -1

    extrinsic: str | None = None

    def __init__(self) -> None:
        self._pcd_conv: RsbpPcdConv | None = None

    def on_start(self, params: dict) -> None:
        if self.extrinsic:
            # params['extrinsic'] = self._conv_ap500_extrinsic(
            #     self.parse_extrinsic('/App/' + self.extrinsic)
            # )
            pass
        self._pcd_conv = RsbpPcdConv(params)
        self._pcd_conv.register_callback()
        self._pcd_conv.start()
        self._pcd_conv.join()

    def on_stop(self) -> None:
        if self._pcd_conv is not None:
            self._pcd_conv.stop()

    def get_dst_path_list(self):
        return self._pcd_conv.get_dst_path_list()

    @staticmethod
    def _conv_ap500_extrinsic(extrinsic: dict) -> dict:
        # yaw/pitch/roll 축 재매핑 + 90도 roll offset.
        return {
            "x": extrinsic["x"],
            "y": extrinsic["y"],
            "z": extrinsic["z"],
            "yaw": extrinsic["pitch"],
            "roll": extrinsic["yaw"] + math.radians(90),
            "pitch": -extrinsic["roll"],
        }
