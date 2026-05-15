from __future__ import annotations

import json
from typing import List

from python_library.logger.app_logger import AppLogger

from drivers.drivers import Drivers
from drivers.driver import IHardware
# vehicleId → Drivers 매핑. 각 vehicleId 마다 /App/config/{vehicleId}/cpu.json 의 sensor 설정을 로드.
# 클래스명 cVehicles → Vehicles.
class Vehicles(IHardware):
    VEHICLE_ID = 0
    DRIVERS = 1

    def __init__(self) -> None:
        self.vehicles: dict[str, Drivers] = {}

    def _register(self, vehicle: tuple[str, Drivers]) -> None:
        vehicle_id = vehicle[Vehicles.VEHICLE_ID]
        drivers = vehicle[Vehicles.DRIVERS]
        try:
            self.vehicles[vehicle_id] = drivers
        except Exception as e:
            AppLogger.instance().exception(f"Failed to initialize driver {vehicle_id}: {e}")
            raise

    @staticmethod
    def _get_config(file_path: str) -> dict:
        with open(file_path, "r") as f:
            return json.load(f)

    @classmethod
    def load(cls, vehicle_ids: List[str]) -> "Vehicles":
        instance = cls()
        for vehicle_id in vehicle_ids:
            config_path = f"/App/config/{vehicle_id}/cpu.json"
            try:
                config = Vehicles._get_config(config_path)
            except FileNotFoundError:
                # 개발 환경에서는 config가 없을 수 있음 — empty Drivers로 polyfill
                AppLogger.instance().warning(f"Vehicle config not found: {config_path}")
                config = {"sensors": []}
            drivers = Drivers.load(config["sensors"])
            instance._register((vehicle_id, drivers))
        return instance

    def get(self, vehicle_id: str) -> Drivers:
        return self.vehicles[vehicle_id]
