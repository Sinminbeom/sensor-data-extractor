from __future__ import annotations

import math
import time
from queue import Empty

from python_library.logger.app_logger import AppLogger

from common.process.app_process import AppProcess
from config.project_config import ProjectConfig
from config.redis_config import RedisConfig
from define.process_name import EXTRACTOR_MODULE_PREFIX
from task.redis_job_list import RedisJobListStore
from task.task_runner import TaskRunner
from listener.redis_queue_consumer import RedisQueueConsumer
from notification.slack_message_sender import SlackMessageSender
from protocol.error_noti import ErrorNoti
from protocol.job_complete import JobComplete
from protocol.pk_ui_job import PkUiJob
from protocol.pk_ui_job_delete import PkUiJobDelete
from protocol.protocol_meta import E_PROTOCOL_ID, ProtocolMeta
from protocol.protocol_utils import ProtocolUtils
from sensor_category.enum_sensor import E_SENSOR_TYPE


_POLL_INTERVAL = 0.01


class ExtractorManager(AppProcess):
    """Manager process — module 회신 dispatch + UI 잡 요청 수신 + 잡 큐 영속화 + slack 알림.

    Queue 구조:
      - shared_job_queue  : module → manager 회신 (JobComplete / ErrorNoti) 공용 큐
      - shared_queue[name]: manager → module_name 별 잡 분배 큐 (N 개)
    """

    def __init__(self, app_name: str, process_name: str) -> None:
        super().__init__(app_name, process_name)
        self._slack: SlackMessageSender | None = None
        self._redis_consumer: RedisQueueConsumer | None = None
        self._redis_job_list: RedisJobListStore | None = None
        self._task_runner: TaskRunner | None = None
        self._protocol_meta: ProtocolMeta | None = None

        # 잡 분배 상태 (camera 잡 / 그 외 round-robin)
        self._camera_module_cnt: int = 0
        self._total_module_cnt: int = 0
        self._camera_distribute: int = 0
        self._etc_distribute: int = 0
        self._has_camera_module: bool = False

    # --- entry point ---

    def action(self) -> None:
        try:
            self._set_config()
            self._init_runtime()
            AppLogger.instance().info(f"[{self.name}] ExtractorManager start")

            # shared_job_queue 직접 폴링 — module 회신 (JobComplete / ErrorNoti).
            comm_queue = self._shared_job_queue
            assert self._protocol_meta is not None
            while not self.is_stop():
                try:
                    raw = comm_queue.get_nowait()
                except Empty:
                    time.sleep(_POLL_INTERVAL)
                    continue
                self._dispatch_module_reply(self._protocol_meta.decode_body(raw))

        except Exception as e:
            AppLogger.instance().exception(e)
            raise
        finally:
            self._shutdown()

    # --- init ---

    def _init_runtime(self) -> None:
        self._protocol_meta = ProtocolMeta.instance()
        ProtocolUtils.instance().initialize()

        cfg = ProjectConfig.instance()
        self._calculate_module_distribution(cfg)

        redis_config = RedisConfig(cfg)
        self._redis_job_list = RedisJobListStore(redis_config)
        self._redis_job_list.connect()

        self._slack = SlackMessageSender()
        self._slack.start()

        self._task_runner = TaskRunner(
            self._slack,
            self._redis_job_list,
            self.next_target_module,
            self.dispatch_to_module,
        )
        self._task_runner.start()

        # Redis COM_QUEUE polling — UI 잡 요청/삭제 수신
        self._redis_consumer = RedisQueueConsumer(
            self._handle_redis_bulk, redis_config
        )
        self._redis_consumer.start()

    def _calculate_module_distribution(self, cfg: ProjectConfig) -> None:
        # module_count = process_count - 1 (manager 1 개 제외)
        self._total_module_cnt = max(0, cfg.process_count - 1)

        camera_ratio = int(
            cfg.get_config(
                ProjectConfig.E_CATE_TYPE.COMMON,
                ProjectConfig.E_CATE_ELE_COMMON.CAMERA_RATIO,
            )
        )
        self._camera_module_cnt = math.ceil(self._total_module_cnt * camera_ratio / 100)

        self._has_camera_module = "AM20" in cfg.module_types
        # AM20 모듈 활성화면 etc module 시작 인덱스는 camera 영역 다음부터
        self._etc_distribute = self._camera_module_cnt if self._has_camera_module else 0

    def _shutdown(self) -> None:
        for stop_fn in (
            (self._redis_consumer.stop if self._redis_consumer else None),
            (self._slack.stop if self._slack else None),
            (self._redis_job_list.disconnect if self._redis_job_list else None),
        ):
            if stop_fn is None:
                continue
            try:
                stop_fn()
            except Exception:
                pass

    # --- dispatch ---

    def _dispatch_module_reply(self, packet) -> None:
        """module 회신: JobComplete / ErrorNoti."""
        if isinstance(packet, JobComplete):
            assert self._task_runner is not None
            self._task_runner.complete(packet.vehicleId, packet.jobId)
        elif isinstance(packet, ErrorNoti):
            assert self._slack is not None
            self._slack.send(packet.comment)

    def _handle_redis_bulk(self, bulk: list[str]) -> None:
        """COM_QUEUE raw json → 디코드 + UI 요청 dispatch."""
        assert self._protocol_meta is not None
        for raw in bulk:
            try:
                packet = self._protocol_meta.decode_body(raw)
            except Exception as e:
                AppLogger.instance().exception(f"Redis bulk decode failed: {e} ({raw})")
                continue
            pid = packet.protocolId
            AppLogger.instance().info(f"AssignJob Start -> {pid}")
            self._dispatch_ui_request(pid, packet)

    def _dispatch_ui_request(self, protocol_id: str, packet) -> None:
        """UI 요청: UI_JOB_REQUEST / UI_JOB_DELETE."""
        assert self._task_runner is not None
        if protocol_id == E_PROTOCOL_ID.UI_JOB_REQUEST.value:
            assert isinstance(packet, PkUiJob)
            self._task_runner.push(packet)
        elif protocol_id == E_PROTOCOL_ID.UI_JOB_DELETE.value:
            assert isinstance(packet, PkUiJobDelete)
            self._task_runner.delete(packet)

    # --- job routing & dispatch ---

    def next_target_module(self, sensor_type: str) -> str:
        """다음 routing target module 이름 결정 (round-robin).

        camera 모듈은 [0..camera_module_cnt) round-robin,
        그 외는 [camera_module_cnt..total_module_cnt) round-robin (camera 비활성화면 [0..total_module_cnt)).
        """
        if sensor_type == E_SENSOR_TYPE.CAMERA:
            target = f"{EXTRACTOR_MODULE_PREFIX}{self._camera_distribute}"
            self._camera_distribute = (self._camera_distribute + 1) % max(
                1, self._camera_module_cnt
            )
        else:
            target = f"{EXTRACTOR_MODULE_PREFIX}{self._etc_distribute}"
            self._etc_distribute += 1
            if self._etc_distribute >= self._total_module_cnt:
                self._etc_distribute = (
                    self._camera_module_cnt if self._has_camera_module else 0
                )
        return target

    def dispatch_to_module(self, target_name: str, packet) -> None:
        """이미 결정된 target module 큐에 packet 직렬화해 push."""
        self.push_shared_queue(target_name, packet.to_json())
