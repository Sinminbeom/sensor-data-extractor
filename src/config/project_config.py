from python_library.configure.app_config import AppConfig
from python_library.define.enum import IENUM
# AppConfig (python-library) 상속 — singleton 패턴 + ini 파일 로딩은 python-library가 담당
class ProjectConfig(AppConfig):
    DEFAULT_CONFIG_PATH = "./conf/application.conf"
    DEFAULT_LOGGING_CONFIG_PATH = "./conf/logging.conf"
    LOGGER_BASE_NAME = "sensor-data-extractor"

    class E_CATE_TYPE(IENUM):
        COMMON = "COMMON"
        PROCESSING = "PROCESSING"
        PROCESS = "PROCESS"
        SRC_STORAGE = "SRC_STORAGE"
        DST_STORAGE = "DST_STORAGE"
        REDIS = "REDIS"
        REST = "REST"

    class E_CATE_ELE_COMMON(IENUM):
        PROJECT_NAME = "PROJECT_NAME"
        CHANNEL_NAME = "CHANNEL_NAME"
        SLACK_URL = "SLACK_URL"
        SLACK_CHANNEL_NAME = "SLACK_CHANNEL_NAME"
        DELAY_TIME = "DELAY_TIME"
        TEST_SUFFIX = "TEST_SUFFIX"
        TEST_PREFIX = "TEST_PREFIX"
        CAMERA_RATIO = "CAMERA_RATIO"

    class E_CATE_ELE_PROCESSING(IENUM):
        MODULE_TYPES = "MODULE_TYPES"
        SENSOR_NAMES = "SENSOR_NAMES"
        VEHICLE_IDS = "VEHICLE_IDS"

    class E_CATE_ELE_PROCESS(IENUM):
        PROCESS_COUNT = "PROCESS_COUNT"
        JOB_QUEUE_COUNT = "JOB_QUEUE_COUNT"
        VOLUMES_PLACEHOLDER = "VOLUMES_PLACEHOLDER"
        TMP_PCAP_PATH = "TMP_PCAP_PATH"
        TMP_RESULT_PATH = "TMP_RESULT_PATH"
    # python-library IStorage 도입 후 storage 종류는 TYPE 키 하나로 통합 (현재 LOCAL only).
    # 추후 Google Drive 등 추가 시 TYPE 값에 따라 storage builder가 분기.
    class E_CATE_ELE_STORAGE(IENUM):
        TYPE = "TYPE"   # 현재는 "LOCAL"만 지원. 추후 "GOOGLE_DRIVE" 등 추가 예정
        ROOT = "ROOT"   # LocalStorage 기준 절대 경로 루트 (예: "/data/normalized")

    class E_CATE_ELE_REDIS(IENUM):
        IP = "IP"
        PORT = "PORT"
        COM_QUEUE_NAME = "COM_QUEUE_NAME"
        JOB_LIST_QUEUE_NAME = "JOB_LIST_QUEUE_NAME"

    class E_CATE_ELE_REST(IENUM):
        BIND_IP = "BIND_IP"
        BIND_PORT = "BIND_PORT"

    def __init__(self) -> None:
        super().__init__()

        self.project_name = self.get_config(
            ProjectConfig.E_CATE_TYPE.COMMON, ProjectConfig.E_CATE_ELE_COMMON.PROJECT_NAME
        )
        self.channel_name = self.get_config(
            ProjectConfig.E_CATE_TYPE.COMMON, ProjectConfig.E_CATE_ELE_COMMON.CHANNEL_NAME
        )

        self.process_count = int(self.get_config(
            ProjectConfig.E_CATE_TYPE.PROCESS, ProjectConfig.E_CATE_ELE_PROCESS.PROCESS_COUNT
        ))
        self.job_queue_count = int(self.get_config(
            ProjectConfig.E_CATE_TYPE.PROCESS, ProjectConfig.E_CATE_ELE_PROCESS.JOB_QUEUE_COUNT
        ))
        self.tmp_volumes = self._parse_delimited(self.get_config(
            ProjectConfig.E_CATE_TYPE.PROCESS, ProjectConfig.E_CATE_ELE_PROCESS.VOLUMES_PLACEHOLDER
        ))
        self.tmp_pcap_path = self.get_config(
            ProjectConfig.E_CATE_TYPE.PROCESS, ProjectConfig.E_CATE_ELE_PROCESS.TMP_PCAP_PATH
        )
        self.tmp_result_path = self.get_config(
            ProjectConfig.E_CATE_TYPE.PROCESS, ProjectConfig.E_CATE_ELE_PROCESS.TMP_RESULT_PATH
        )

        self.module_types = self._parse_delimited(self.get_config(
            ProjectConfig.E_CATE_TYPE.PROCESSING, ProjectConfig.E_CATE_ELE_PROCESSING.MODULE_TYPES
        ))
        self.sensor_names = self._parse_delimited(self.get_config(
            ProjectConfig.E_CATE_TYPE.PROCESSING, ProjectConfig.E_CATE_ELE_PROCESSING.SENSOR_NAMES
        ))
        self.vehicle_ids = self._parse_delimited(self.get_config(
            ProjectConfig.E_CATE_TYPE.PROCESSING, ProjectConfig.E_CATE_ELE_PROCESSING.VEHICLE_IDS
        ))
        # 본 구현은 storage 종류 + root 만 받고, 실제 path는 worker / extractor가 조합.
        self.src_storage_type = self.get_config(
            ProjectConfig.E_CATE_TYPE.SRC_STORAGE, ProjectConfig.E_CATE_ELE_STORAGE.TYPE
        )
        self.src_storage_root = self.get_config(
            ProjectConfig.E_CATE_TYPE.SRC_STORAGE, ProjectConfig.E_CATE_ELE_STORAGE.ROOT
        )
        self.dst_storage_type = self.get_config(
            ProjectConfig.E_CATE_TYPE.DST_STORAGE, ProjectConfig.E_CATE_ELE_STORAGE.TYPE
        )
        self.dst_storage_root = self.get_config(
            ProjectConfig.E_CATE_TYPE.DST_STORAGE, ProjectConfig.E_CATE_ELE_STORAGE.ROOT
        )

        self.bind_ip = self.get_config(
            ProjectConfig.E_CATE_TYPE.REST, ProjectConfig.E_CATE_ELE_REST.BIND_IP
        )
        self.bind_port = int(self.get_config(
            ProjectConfig.E_CATE_TYPE.REST, ProjectConfig.E_CATE_ELE_REST.BIND_PORT
        ))

    @staticmethod
    def _parse_delimited(raw: str, delim: str = "|") -> list[str]:
        if not raw:
            return []
        return [s.strip() for s in raw.split(delim) if s.strip()]
