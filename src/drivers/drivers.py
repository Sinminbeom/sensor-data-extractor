from __future__ import annotations

import inspect
import pkgutil
from importlib import import_module
from typing import List

import jsons

from python_library.logger.app_logger import AppLogger

from config.project_config import ProjectConfig
from drivers.driver import IDriver, IHardware
# 차량 한 대가 보유한 driver 모음. 'drivers' 패키지에서 자동 import + sensor 설정으로 register.
# 클래스명 cDrivers → Drivers.
class Drivers(IHardware):
    _is_init: list[bool] = [False]
    _drivers: dict[str, IDriver] = {}

    def __init__(self) -> None:
        self._drivers = {}

    def _register(self, driver: IDriver) -> None:
        try:
            self._drivers[driver.name] = driver
        except Exception as e:
            AppLogger.instance().exception(f"Failed to initialize driver {driver.name}: {e}")
            raise

    @staticmethod
    def _import_all() -> None:
        dirname = "drivers"
        for _, package_name, _ in pkgutil.iter_modules([dirname]):
            full_name = f"{dirname}.{package_name}"
            try:
                module = import_module(full_name)
            except Exception:
                continue
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    globals()[name] = obj

    @staticmethod
    def _str_to_class(classname: str):
        module = import_module(f"drivers.{classname.lower()}.driver")
        return getattr(module, classname)

    @classmethod
    def load(cls, sensors: List[dict]) -> "Drivers":
        instance = cls()
        Drivers._import_all()

        module_types = ProjectConfig.instance().module_types

        for sensor in sensors:
            driver_name: str = sensor["driver"]
            if driver_name not in module_types:
                continue
            del sensor["driver"]
            driver_cls = Drivers._str_to_class(driver_name)
            instance._register(jsons.load(sensor, driver_cls))

        Drivers._is_init[0] = True
        return instance

    def get(self, driver_name: str) -> IDriver:
        return self._drivers[driver_name]

    def stop_all(self) -> None:
        for driver in self._drivers.values():
            driver.on_stop()
            AppLogger.instance().info(f"Driver {driver.name} stopped.")
