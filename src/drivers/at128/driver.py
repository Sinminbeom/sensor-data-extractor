from typing import List

from drivers.at128.pcd_conv import At128PcdConv
from drivers.driver import IDriver
# 차량(Vehicles)이 보유한 AT128 LiDAR driver. ExtractorModule가 on_start/OnStop를 호출.
class At128(IDriver):
    name: str = "AT128"

    src_ip: str = "localhost"
    protocol: str = "udp"
    dst_ip: str = "unknown"
    dst_port: int = -1
    extrinsic: str | None = None

    def __init__(self) -> None:
        self._pcd_conv: At128PcdConv | None = None

    def on_start(self, params: dict) -> None:
        if self.extrinsic:
            # params['extrinsic'] = self.parse_extrinsic('/App/' + self.extrinsic)
            pass
        self._pcd_conv = At128PcdConv(params)
        self._pcd_conv.start()

    def get_is_end_save_pcd(self) -> bool:
        return self._pcd_conv.get_is_end_save_pcd()

    def get_dst_path_list(self) -> List[str]:
        return self._pcd_conv.get_dst_path_list()

    def on_stop(self) -> None:
        if self._pcd_conv is None:
            return
        self._pcd_conv.join()
        self._pcd_conv.stop()
