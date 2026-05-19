from __future__ import annotations

import time
from datetime import datetime
from typing import Tuple

from python_library.logger.app_logger import AppLogger
from python_library.storage.s3.s3_storage_factory import S3StorageFactory
from python_library.storage.s3.s3_storage_info_factory import S3StorageInfoFactory
from python_library.storage.storage import IStorage

from common.process.app_process import AppProcess
from config.project_config import ProjectConfig
from consumer.consumer_registry import ConsumerRegistry
from consumer.message_consumer import MessageConsumer
from drivers.vehicles import Vehicles
from extractor.extract_context import ExtractContext
from extractor.gstreamer.cpp_library import build_cpp_library_for_camera
from extractor.gstreamer.state import GstreamerState
from protocol.error_noti import ErrorNoti
from protocol.job_complete import JobComplete
from protocol.job_packet import JobPacket
from protocol.protocol_meta import E_PROTOCOL_ID, E_RECEIVER, ProtocolMeta


class ExtractorWorker(AppProcess):
    """JobPacket 수신 → 모듈 타입별 추출 → JobComplete/ErrorNoti 회신.

    python-library MultiProcessManager 가 shared queue 를 자동 inject:
      - self._shared_queue[self.name] : manager → 이 worker 잡 큐 (RECV)
      - self._shared_job_queue        : worker → manager 회신 큐 (SEND)
    """

    def __init__(self, app_name: str, process_name: str) -> None:
        super().__init__(app_name, process_name)

        self._disks: list[str] = []
        self._tmp_pcap: str = ""
        self._tmp_result: str = ""
        self._disk_select_index = 0
        self._source_storage: IStorage | None = None
        self._destination_storage: IStorage | None = None
        self._source_storage_root: str = ""
        self._destination_storage_root: str = ""

        self._consumer_registry: ConsumerRegistry | None = None
        self._gstreamer_state = GstreamerState()
        self._vehicles: Vehicles | None = None

    def _init_config(self) -> None:
        cfg = ProjectConfig.instance()
        self._disks = cfg.tmp_volumes
        self._tmp_pcap = cfg.tmp_pcap_path
        self._tmp_result = cfg.tmp_result_path

    def _init_runtime(self) -> None:
        self._consumer_registry = ConsumerRegistry()
        # shared_queue[self.name] = manager 가 push 한 잡 큐. comm 회신은 self._shared_job_queue 로 SEND 전용.
        self._consumer_registry.register(
            "job",
            MessageConsumer(self._shared_queue[self.name], lambda packet: self._dispatch(packet)),
        )

        ProtocolMeta.initialize()
        self._vehicles = Vehicles.load(ProjectConfig.instance().vehicle_ids)

        cfg = ProjectConfig.instance()
        self._source_storage = S3StorageFactory(S3StorageInfoFactory()).create_storage()
        self._source_storage.connect()
        self._source_storage_root = cfg.src_storage_root
        self._destination_storage = S3StorageFactory(S3StorageInfoFactory()).create_storage()
        self._destination_storage.connect()
        self._destination_storage_root = cfg.dst_storage_root

    def action(self) -> None:
        try:
            self._set_config()
            self._init_config()
            self._init_runtime()

            AppLogger.instance().info(f"[{self.name}] ExtractorWorker start")
            self._consumer_registry.start_all()

            while not self.is_stop():
                time.sleep(0.01)

        except Exception as e:
            AppLogger.instance().exception(e)
        finally:
            self._on_interrupt()

    def _on_interrupt(self) -> None:
        if self._source_storage is not None:
            try:
                self._source_storage.disconnect()
            except Exception:
                pass
        if self._destination_storage is not None:
            try:
                self._destination_storage.disconnect()
            except Exception:
                pass

    def get_process_number(self) -> int:
        return int(self.name.split("_")[-1])

    def get_name(self) -> str:
        return self.name

    # --- protocol dispatch ---

    def _dispatch(self, packet) -> None:
        # replayer 패턴: ProtocolMeta가 (process, packet) 시그니처 handler를 반환 → 호출.
        handler = ProtocolMeta.get_receive_handler(
            packet.get_protocol_id(), E_RECEIVER.EXTRACTOR_WORKER
        )
        handler(self, packet)

    # --- receive handlers (ProtocolHandler.worker_* 가 호출) ---

    def handle_job_request(self, packet: JobPacket) -> None:
        try:
            AppLogger.instance().info(f"JOB START -> Job ID : {packet.get_job_id()}")

            tmp_pcap_path, tmp_result_path = self._get_tmp_saved_path()
            ctx = ExtractContext(
                name=self.name,
                source_storage=self._source_storage,
                destination_storage=self._destination_storage,
                tmp_pcap_saved_path=tmp_pcap_path,
                tmp_result_saved_path=tmp_result_path,
                protocol=packet,
                gstreamer_state=self._gstreamer_state,
                vehicles=self._vehicles,
                cpp_library=build_cpp_library_for_camera(self.get_process_number()),
            )

            extract_fn = ProtocolMeta.get_extractor(
                E_PROTOCOL_ID.JOB_REQUEST, packet.get_module_type()
            )
            extract_fn(ctx)

            self._send(JobComplete(
                self.name,
                packet.get_job_id(),
                packet.get_vehicle_id(),
                packet.get_sensor_type(),
                packet.get_module_type(),
            ))
        except Exception as e:
            error_msg = (
                f"[{self.name}] Exception\n"
                f"Job Id : {packet.get_job_id()}\n"
                f"Exception Time : {datetime.now()}\n"
                f"Message : {e}"
            )
            AppLogger.instance().exception(error_msg)
            self._send(ErrorNoti(self.name, error_msg, packet.get_job_id(), "UNKNOWN"))
        time.sleep(0)

    # --- helpers ---

    def _send(self, protocol) -> None:
        # _shared_job_queue 는 manager 의 BulkMessageConsumer 가 watch — push 만 하면 됨.
        self.push_shared_job_queue(protocol)

    def _get_tmp_saved_path(self) -> Tuple[str, str]:
        tmp_pcap_path = self._disks[self._disk_select_index] + self._tmp_pcap
        tmp_result_path = self._disks[self._disk_select_index] + self._tmp_result
        self._disk_select_index = (self._disk_select_index + 1) % len(self._disks)
        return tmp_pcap_path, tmp_result_path
