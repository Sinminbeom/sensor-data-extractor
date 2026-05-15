from sensor_category.enum_sensor import E_CAMERA, E_GNSS, E_IMU, E_LIDAR, E_SENSOR_TYPE

class SensorCategory:
    """sensor_id ↔ 센서 카테고리 매핑 정적 레지스트리.

    추출기 라우팅(sensor_id → 모듈 type) 및 스토리지 경로 구성 시 사용.
    E_LIDAR / E_GNSS / E_CAMERA / E_IMU 클래스 멤버를 introspection으로 훑어
    매핑 테이블을 자동 구성하므로, 새 센서를 enum에 추가하면 자동 반영된다.

    경로 구성 예시:
        {root}/{prefix}/{vehicle_id}/{category}/{sensor_id_lower}/...
    """

    @staticmethod
    def _build_map() -> dict[str, str]:
        result: dict[str, str] = {}
        for cls, category in (
            (E_LIDAR, E_SENSOR_TYPE.LIDAR.lower()),
            (E_GNSS, E_SENSOR_TYPE.GNSS.lower()),
            (E_CAMERA, E_SENSOR_TYPE.CAMERA.lower()),
            (E_IMU, E_SENSOR_TYPE.IMU.lower()),
        ):
            for name, value in vars(cls).items():
                if name.startswith("_") or not isinstance(value, str):
                    continue
                result[value] = category
        return result

    _BY_SENSOR_ID: dict[str, str] = _build_map()

    @classmethod
    def get(cls, sensor_id: str) -> str | None:
        return cls._BY_SENSOR_ID.get(sensor_id)

    @classmethod
    def has(cls, sensor_id: str) -> bool:
        return sensor_id in cls._BY_SENSOR_ID

    @classmethod
    def all_sensor_ids(cls) -> list[str]:
        return sorted(cls._BY_SENSOR_ID.keys())
