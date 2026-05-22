from __future__ import annotations

from define.module_type import E_MODULE_TYPE
from extractor.extract_context import ExtractContext
from extractor.sensors.am20_extract import Am20Extract
from extractor.sensors.at128_extract import At128Extract
from extractor.sensors.gnss_extract import GnssExtract
from extractor.sensors.imu_extract import ImuExtract
from extractor.sensors.rsbp_extract import RsbpExtract


class ExtractRegistry:
    """module_type → Extract.extract dispatch table."""

    _TABLE = {
        E_MODULE_TYPE.AT128: At128Extract.extract,
        E_MODULE_TYPE.RSBP: RsbpExtract.extract,
        E_MODULE_TYPE.AM20: Am20Extract.extract,
        E_MODULE_TYPE.GNSS: GnssExtract.extract,
        E_MODULE_TYPE.IMU: ImuExtract.extract,
    }

    @staticmethod
    def extract(module_type: str, ctx: ExtractContext) -> None:
        ExtractRegistry._TABLE[module_type](ctx)
