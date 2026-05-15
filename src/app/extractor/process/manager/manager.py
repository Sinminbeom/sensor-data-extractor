from __future__ import annotations

import math
import time
from typing import List, Optional

from python_library.logger.app_logger import AppLogger

from common.process.app_process import AppProcess
from config.project_config import ProjectConfig
from config.redis_config import RedisConfig
from consumer.bulk_message_consumer import BulkMessageConsumer
from consumer.consumer_registry import ConsumerRegistry
from task.redis_job_list import RedisJobListStore
from task.task_runner import TaskRunner
from messaging.redis_publisher import RedisPublisher  # noqa: F401  (생성자에서 사용 안 하지만 의존 명시)
from messaging.redis_subscriber import RedisSubscriber
from messaging.slack_message_sender import SlackMessageSender
from protocol.error_noti import ErrorNoti
from protocol.job_complete import JobComplete
from protocol.pk_ui_job import PkUiJob
from protocol.pk_ui_job_delete import PkUiJobDelete
from protocol.protocol_meta import E_RECEIVER, ProtocolMeta
from protocol.protocol_utils import ProtocolUtils
from sensor_category.enum_sensor import E_SENSOR_TYPE
from utils.json_util import JsonUtil


WORKER_NAME_PREFIX = "EXTRACTOR_WORKER_"


class ExtractorManager(AppProcess):
    """Manager process — worker 회신 dispatch + UI 잡 요청 수신 + 잡 큐 영속화 + slack 알림.

    python-library MultiProcessManager 가 lifecycle (start/join) 을 담당.
    Manager 도 worker 와 동일한 abProcess 라서 자식 process 로 시작되며,
    set_shared_job_queue / set_shared_queue 가 자동으로 inject 됨.

    Queue 구조:
      - shared_job_queue  : worker → manager 회신 (JobComplete / ErrorNoti) 공용 큐
      - shared_queue[name]: manager → worker_name 별 잡 분배 큐 (N 개)
    """

    POLL_INTERVAL = 0.01

    def __init__(self, app_name: str, process_name: str) -> None:
        super().__init__(app_name, process_name)
        self._consumer_registry: ConsumerRegistry | None = None
        self._slack: SlackMessageSender | None = None
        self._redis_subscriber: RedisSubscriber | None = None
        self._redis_job_list: RedisJobListStore | None = None
        self._task_runner: TaskRunner | None = None

        # 잡 분배 상태 (camera 잡 / 그 외 round-robin)
        self._camera_worker_cnt: int = 0
        self._total_worker_cnt: int = 0
        self._camera_distribute: int = 0
        self._etc_distribute: int = 0
        self._has_camera_module: bool = False

    # --- entry point ---

    def action(self) -> None:
        try:
            self._set_config()
            self._init_runtime()
            AppLogger.instance().info(f"[{self.name}] ExtractorManager start")

            while not self.is_stop():
                time.sleep(ExtractorManager.POLL_INTERVAL)

        except Exception as e:
            AppLogger.instance().exception(e)
            raise
        finally:
            self._shutdown()

    # --- init ---

    def _init_runtime(self) -> None:
        ProtocolMeta.initialize()
        ProtocolUtils.instance().initialize()

        cfg = ProjectConfig.instance()
        self._calculate_worker_distribution(cfg)

        redis_config = RedisConfig(cfg)
        self._redis_job_list = RedisJobListStore(redis_config)
        self._redis_job_list.connect()

        self._slack = SlackMessageSender()
        self._slack.start()

        self._task_runner = TaskRunner(
            self._slack, self._redis_job_list, self.assign_job
        )
        self._task_runner.start()

        # Redis COM_QUEUE polling — UI 잡 요청/삭제 수신
        self._redis_subscriber = RedisSubscriber(
            self._handle_redis_bulk, redis_config
        )
        self._redis_subscriber.start()

        # shared_job_queue (worker → manager 회신) BulkMessageConsumer 등록
        self._consumer_registry = ConsumerRegistry()
        self._consumer_registry.register(
            "comm",
            BulkMessageConsumer(self._shared_job_queue, self._handle_bulk),
        )
        self._consumer_registry.start_all()

    def _calculate_worker_distribution(self, cfg: ProjectConfig) -> None:
        # worker_count = process_count - 1 (manager 1개 제외)
        self._total_worker_cnt = max(0, cfg.process_count - 1)

        camera_ratio = int(
            cfg.get_config(
                ProjectConfig.E_CATE_TYPE.COMMON,
                ProjectConfig.E_CATE_ELE_COMMON.CAMERA_RATIO,
            )
        )
        self._camera_worker_cnt = math.ceil(self._total_worker_cnt * camera_ratio / 100)

        self._has_camera_module = "AM20" in cfg.module_types
        # AM20 모듈 활성화면 etc 워커 시작 인덱스는 camera 영역 다음부터
        self._etc_distribute = self._camera_worker_cnt if self._has_camera_module else 0

    def _shutdown(self) -> None:
        try:
            if self._consumer_registry is not None:
                self._consumer_registry.stop_all()
        except Exception:
            pass
        try:
            if self._redis_subscriber is not None:
                self._redis_subscriber.stop()
        except Exception:
            pass
        try:
            if self._slack is not None:
                self._slack.stop()
        except Exception:
            pass
        try:
            if self._redis_job_list is not None:
                self._redis_job_list.disconnect()
        except Exception:
            pass

    # --- protocol dispatch ---

    def _dispatch(self, packet) -> None:
        handler = ProtocolMeta.get_receive_handler(
            packet.get_protocol_id(), E_RECEIVER.EXTRACTOR_MANAGER
        )
        handler(self, packet)

    def _handle_bulk(self, bulk: list) -> None:
        # shared_job_queue 에서 BulkMessageConsumer 가 pop 한 회신 packet 들.
        for packet in bulk:
            self._dispatch(packet)

    def _handle_redis_bulk(self, bulk: list[str]) -> None:
        # COM_QUEUE 의 raw json. protocolId 추출 후 ProtocolMeta decoder 로 정확한 packet 생성.
        for raw in bulk:
            try:
                meta = JsonUtil.from_json(raw, PkUiJob)
                pid = meta.get_protocol_id()
                packet = ProtocolMeta.get_json_decoder(pid)(raw)
            except Exception as e:
                AppLogger.instance().exception(f"Redis bulk decode failed: {e} ({raw})")
                continue
            AppLogger.instance().info(f"AssignJob Start -> {pid}")
            self._dispatch(packet)

    # --- receive handlers (ProtocolHandler.manager_* 가 호출) ---

    def handle_job_complete(self, packet: JobComplete) -> None:
        assert self._task_runner is not None
        self._task_runner.complete(packet.get_vehicle_id(), packet.get_job_id())

    def handle_error_noti(self, packet: ErrorNoti) -> None:
        assert self._slack is not None
        self._slack.send(packet.get_comment())

    def handle_ui_job_request(self, packet: PkUiJob) -> None:
        assert self._task_runner is not None
        self._task_runner.push(packet)

    def handle_ui_job_delete(self, packet: PkUiJobDelete) -> None:
        assert self._task_runner is not None
        self._task_runner.delete(packet)

    # --- job assignment ---

    def assign_job(self, protocol) -> None:
        """JobPacket 1 건을 worker process 의 shared_queue 에 push.

        camera 모듈은 [0..camera_worker_cnt) round-robin,
        그 외는 [camera_worker_cnt..total_worker_cnt) round-robin (camera 모듈 비활성화면 [0..total_worker_cnt)).
        """
        if protocol.sensorType == E_SENSOR_TYPE.CAMERA:
            target_name = f"{WORKER_NAME_PREFIX}{self._camera_distribute}"
            self._camera_distribute = (self._camera_distribute + 1) % max(
                1, self._camera_worker_cnt
            )
        else:
            target_name = f"{WORKER_NAME_PREFIX}{self._etc_distribute}"
            self._etc_distribute += 1
            if self._etc_distribute >= self._total_worker_cnt:
                self._etc_distribute = (
                    self._camera_worker_cnt if self._has_camera_module else 0
                )

        self.push_shared_queue(target_name, protocol)
