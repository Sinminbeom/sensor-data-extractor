from __future__ import annotations

from python_library.define.enum import IENUM
from python_library.singleton.singleton import Singleton

from define.module_type import E_MODULE_TYPE
from sensor_category.enum_sensor import E_CAMERA, E_GNSS, E_LIDAR, E_SENSOR_TYPE
from utils.collection_utils import CollectionUtils
class E_CATE(IENUM):
    MODULE_TYPE = "MODULE_TYPE"
    SENSOR_TYPE = "SENSOR_TYPE"
# 2단계 category 트리:
#   cateQueue[MODULE_TYPE][AT128] = [AT128_ROOF_FRONT, ...]
#   cateQueue[SENSOR_TYPE][LIDAR] = [AT128_ROOF_FRONT, ...]
# 클래스명 cSensorCate → SensorRegistry.
class SensorRegistry(metaclass=Singleton):
    def __init__(self) -> None:
        self.cate_queue: dict[str, dict[str, list[str]]] = {}

    def initialize(self) -> "SensorRegistry":
        self.cate_queue = {}
        return self

    # --- registration ---

    def register_sensor(self) -> None:
        self._set_cate2(E_CATE.SENSOR_TYPE, E_SENSOR_TYPE.GNSS, E_GNSS.GNSS)

        for sensor in (
            E_LIDAR.AT128_ROOF_FRONT,
            E_LIDAR.AT128_ROOF_RIGHT,
            E_LIDAR.AT128_ROOF_REAR,
            E_LIDAR.AT128_ROOF_LEFT,
            E_LIDAR.RSBP_BUMP_FRONT,
            E_LIDAR.RSBP_BUMP_RIGHT,
            E_LIDAR.RSBP_BUMP_REAR,
            E_LIDAR.RSBP_BUMP_LEFT,
        ):
            self._set_cate2(E_CATE.SENSOR_TYPE, E_SENSOR_TYPE.LIDAR, sensor)

        for sensor in (
            E_CAMERA.AM20_FRONT_CENTER_RIGHT_DOWN,
            E_CAMERA.AM20_FRONT_RIGHT_REAR,
            E_CAMERA.AM20_REAR_CENTER_RIGHT,
            E_CAMERA.AM20_FRONT_LEFT_REAR,
            E_CAMERA.AM20_REAR_RIGHT_EDGE,
            E_CAMERA.AM20_LEFT_REAR_EDGE,
            E_CAMERA.AM20_FRONT_CENTER_LEFT_UP,
            E_CAMERA.AM20_FRONT_CENTER_RIGHT_UP,
            E_CAMERA.AM20_FRONT_RIGHT_FRONT,
            E_CAMERA.AM20_FRONT_LEFT_FRONT,
        ):
            self._set_cate2(E_CATE.SENSOR_TYPE, E_SENSOR_TYPE.CAMERA, sensor)

    def register_module(self) -> None:
        self._set_cate2(E_CATE.MODULE_TYPE, E_MODULE_TYPE.IMU, E_GNSS.GNSS)

        for sensor in (
            E_LIDAR.AT128_ROOF_FRONT,
            E_LIDAR.AT128_ROOF_RIGHT,
            E_LIDAR.AT128_ROOF_REAR,
            E_LIDAR.AT128_ROOF_LEFT,
        ):
            self._set_cate2(E_CATE.MODULE_TYPE, E_MODULE_TYPE.AT128, sensor)

        for sensor in (
            E_LIDAR.RSBP_BUMP_FRONT,
            E_LIDAR.RSBP_BUMP_RIGHT,
            E_LIDAR.RSBP_BUMP_REAR,
            E_LIDAR.RSBP_BUMP_LEFT,
        ):
            self._set_cate2(E_CATE.MODULE_TYPE, E_MODULE_TYPE.RSBP, sensor)

        for sensor in (
            E_CAMERA.AM20_FRONT_CENTER_RIGHT_DOWN,
            E_CAMERA.AM20_FRONT_RIGHT_REAR,
            E_CAMERA.AM20_REAR_CENTER_RIGHT,
            E_CAMERA.AM20_FRONT_LEFT_REAR,
            E_CAMERA.AM20_REAR_RIGHT_EDGE,
            E_CAMERA.AM20_LEFT_REAR_EDGE,
            E_CAMERA.AM20_FRONT_CENTER_LEFT_UP,
            E_CAMERA.AM20_FRONT_CENTER_RIGHT_UP,
            E_CAMERA.AM20_FRONT_RIGHT_FRONT,
            E_CAMERA.AM20_FRONT_LEFT_FRONT,
        ):
            self._set_cate2(E_CATE.MODULE_TYPE, E_MODULE_TYPE.AM20, sensor)

    # --- internal helpers ---

    def _extend_cate1(self, cate1: str) -> dict:
        return CollectionUtils.dict_extends(self.cate_queue, cate1, lambda: {})

    def _extend_cate2(self, cate1: str, cate2: str) -> list:
        return CollectionUtils.dict_extends(self._extend_cate1(cate1), cate2, lambda: [])

    def _set_cate2(self, cate1: str, cate2: str, value: str) -> None:
        self._extend_cate2(cate1, cate2).append(value)

    # --- public lookup ---

    def get_cate1(self, cate1: str) -> dict | None:
        return self.cate_queue.get(cate1)

    def get_cate2(self, cate1: str, cate2: str) -> list | None:
        c1 = self.get_cate1(cate1)
        return c1.get(cate2) if c1 else None

    def get_cate2_by_value(self, cate1: str, value: str) -> str | None:
        c1 = self.get_cate1(cate1)
        if c1 is None:
            return None
        for cate2, values in c1.items():
            if value in values:
                return cate2
        return None

    def get_cate2_list(self, cate1: str) -> list[str]:
        c1 = self.get_cate1(cate1)
        return list(c1.keys()) if c1 else []

    def get_sensor_name_list(self, *cate) -> list[str]:
        if len(cate) == 1:
            result: list[str] = []
            cate1 = self.get_cate1(cate[0])
            if cate1 is None:
                return result
            for sub in cate1.values():
                result.extend(sub)
            return result
        if len(cate) == 2:
            return self.get_cate2(cate[0], cate[1]) or []
        if len(cate) == 3:
            sub = self.get_cate2(cate[0], cate[1]) or []
            return [v for v in sub if v == cate[2]]
        raise ValueError("get_sensor_name_list expects 1~3 args")
    def init(self) -> "SensorRegistry":
        return self.initialize()

    def register_sensor(self) -> None:
        self.register_sensor()

    def register_module(self) -> None:
        self.register_module()

    def get_cate2_by_value(self, cate1, value):
        return self.get_cate2_by_value(cate1, value)

    def get_cate2_list(self, cate1):
        return self.get_cate2_list(cate1)

    def get_sensor_name_list(self, *cate):
        return self.get_sensor_name_list(*cate)
