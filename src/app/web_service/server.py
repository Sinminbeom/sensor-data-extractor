import base64
import json
from dataclasses import asdict, dataclass

import uvicorn
from fastapi import FastAPI

from python_library.logger.app_logger import AppLogger
from python_library.storage.s3.s3_storage_factory import S3StorageFactory
from python_library.storage.s3.s3_storage_info_factory import S3StorageInfoFactory
from python_library.storage.storage import IStorage

from config.project_config import ProjectConfig
from config.redis_config import RedisConfig
from task.redis_job_list import RedisJobListStore
from messaging.redis_publisher import RedisPublisher
from protocol.pk_ui_job import PkUiJob
from protocol.pk_ui_job_delete import PkUiJobDeleteHelper
from protocol.protocol_meta import ProtocolMeta
from utils.json_util import JsonUtil
# 응답 헬퍼. FastAPI는 dict/list/dataclass를 자동 JSON 직렬화하므로 별도 jsonify 불필요.
@dataclass
class ResponsePayload:
    protocol_id: str
    sender: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
# FastAPI 로 교체. 동작 contract는 그대로 — 모든 endpoint가 동기 GET이고 JSON 반환.
# 디렉터리 entry를 직접 다루지 않으므로, get_file_list 결과에서 첫 segment를 추출해 디렉터리를 흉내낸다.
class WebServiceServer:
    NAME = "UI"
    MARK_TEST = "test"
    MARK_TEST_PATH = "-test"

    def __init__(self) -> None:
        self._app = FastAPI()
        self._config = ProjectConfig.instance()
        self._src_storage: IStorage = S3StorageFactory(S3StorageInfoFactory()).create_storage()
        self._src_storage.connect()
        self._dst_storage: IStorage = S3StorageFactory(S3StorageInfoFactory()).create_storage()
        self._dst_storage.connect()
        self._src_root = self._config.src_storage_root
        self._dst_root = self._config.dst_storage_root

        # Redis: COM_QUEUE 발행 + JOB_LIST_QUEUE 조회 (책임별 분리된 두 클래스)
        redis_config = RedisConfig(self._config)
        self._redis_publisher = RedisPublisher(redis_config)
        self._redis_publisher.connect()
        self._redis_job_list = RedisJobListStore(redis_config)
        self._redis_job_list.connect()

        self._bind_routes()

    def _bind_routes(self) -> None:
        app = self._app

        @app.get("/hello")
        def hello() -> dict:
            return {"message": "Hello, World!"}
        # 디렉터리 구조: <src_root>/<vehicleId>/<sensorType>/<sensorName>/<YYYYMMDD>/...
        @app.get("/normalize-dates")
        def normalize_dates() -> list[str]:
            return self._collect_dates_under(self._src_root)

        @app.get("/normalize-vehicleIds/{date}")
        def normalize_vehicle_ids(date: str) -> list[str]:
            return self._collect_vehicles_on_date(self._src_root, date)
        @app.get("/warehouse/dates")
        def warehouse_dates() -> list[str]:
            return self._list_immediate_subdirs(self._dst_storage, self._dst_root)

        @app.get("/warehouse/vehicleids/{date}")
        def warehouse_vehicle_ids(date: str) -> list[str]:
            path = f"{self._dst_root}/{date}"
            return self._list_immediate_subdirs(self._dst_storage, path)
        @app.get("/extract_req/{date}/{vehicleid}")
        def extract_req(date: str, vehicleid: str) -> dict:
            self._publish_ui_job_request(date, vehicleid)
            return {"result": "ok"}
        @app.get("/extract_req_and_job_lists/{date}/{vehicleid}")
        @app.get("/extract_req_and_job_lists/{date}/{vehicleid}/{mode}")
        def extract_req_and_job_lists(
            date: str, vehicleid: str, mode: str | None = None
        ) -> list[str]:
            self._publish_ui_job_request(date, vehicleid)
            return self._redis_job_list.fetch_all_as_jenkins_names(mode)

        @app.get("/extract_list_req")
        @app.get("/extract_list_req/{mode}")
        def extract_list_req(mode: str | None = None) -> list[str]:
            return self._redis_job_list.fetch_all_as_jenkins_names(mode)
        @app.get("/extract_job_cancel_req/{job_info_str}")
        def extract_job_cancel_req(job_info_str: str) -> dict:
            self._publish_ui_job_delete(job_info_str)
            return {"message": "ok"}
        @app.get("/list/{b64_path}")
        def list_path(b64_path: str) -> list[str]:
            path = base64.urlsafe_b64decode(b64_path.encode()).decode()
            AppLogger.instance().info(f"List path : {path}")
            return [sf.get_file_path() for sf in self._src_storage.get_file_list(path)]

    # --- helpers ---

    def _list_immediate_subdirs(self, storage: IStorage, path: str) -> list[str]:
        """python-library IStorage 위에서 디렉터리 entry를 흉내내는 helper.

        get_file_list 가 재귀 + 파일만 반환하므로, path 바로 다음 segment를 set으로 모은다.
        task_runner._list_immediate_subdirs 와 동일 패턴.
        """
        prefix = path.rstrip("/") + "/"
        names: set[str] = set()
        for sf in storage.get_file_list(path):
            full = sf.get_file_path()
            if not full.startswith(prefix):
                continue
            tail = full[len(prefix):]
            first = tail.split("/", 1)[0]
            if first:
                names.add(first)
        return sorted(names)

    def _collect_dates_under(self, root: str) -> list[str]:
        prefix = root.rstrip("/") + "/"
        dates: set[str] = set()
        for sf in self._src_storage.get_file_list(root):
            full = sf.get_file_path()
            if not full.startswith(prefix):
                continue
            parts = full[len(prefix):].split("/")
            # parts = [vehicleId, sensorType, sensorName, YYYYMMDD, HH, MM, file]
            if len(parts) >= 4:
                dates.add(parts[3])
        return sorted(dates)

    def _collect_vehicles_on_date(self, root: str, date: str) -> list[str]:
        prefix = root.rstrip("/") + "/"
        vehicles: set[str] = set()
        for sf in self._src_storage.get_file_list(root):
            full = sf.get_file_path()
            if not full.startswith(prefix):
                continue
            parts = full[len(prefix):].split("/")
            if len(parts) >= 4 and parts[3] == date:
                vehicles.add(parts[0])
        return sorted(vehicles)

    def _publish_ui_job_request(self, date: str, vehicle_id: str) -> None:
        pk = PkUiJob(
            ProtocolMeta.E_PROTOCOL_ID.UI_JOB_REQUEST,
            WebServiceServer.NAME,
            date,
            vehicle_id,
        )
        self._redis_publisher.publish(JsonUtil.to_json(pk))

    def _publish_ui_job_delete(self, job_info_str: str) -> None:
        delete_packet = PkUiJobDeleteHelper.factory_jenkins_from(job_info_str)
        self._redis_publisher.publish(JsonUtil.to_json(delete_packet))

    def run(self, host: str = "0.0.0.0", port: int = 5001, debug: bool = False) -> None:
        # debug 플래그는 uvicorn의 reload (개발용)으로 매핑.
        uvicorn.run(self._app, host=host, port=port, log_level="debug" if debug else "info")
