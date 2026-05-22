from __future__ import annotations

import time
from datetime import datetime
from queue import Empty
from typing import Tuple

from python_library.logger.app_logger import AppLogger
from python_library.storage.s3.s3_storage_factory import S3StorageFactory
from python_library.storage.s3.s3_storage_info_factory import S3StorageInfoFactory
from python_library.storage.storage import IStorage

from common.process.app_process import AppProcess
from config.project_config import ProjectConfig
from define.process_name import EXTRACTOR_MANAGER
from drivers.vehicles import Vehicles
from extractor.extract_context import ExtractContext
from extractor.extract_registry import ExtractRegistry
from extractor.gstreamer.cpp_library import build_cpp_library_for_camera
from extractor.gstreamer.state import GstreamerState
from protocol.job_request import JobRequest
from protocol.protocol_meta import E_PROTOCOL_ID, ProtocolMeta


_POLL_INTERVAL_EMPTY = 0.1


class ExtractorModule(AppProcess):
    """JobRequest 수신 → 모듈 타입별 추출 → JobComplete/ErrorNoti 회신.

    python-library MultiProcessManager 가 shared queue 자동 inject:
      - self._shared_queue[self.name] : manager → module 잡 큐 (RECV)
      - self._shared_job_queue        : module → manager 회신 큐 (SEND)
    """

    def __init__(self, app_name: str, process_name: str) -> None:
        super().__init__(app_name, process_name)

        self._disks: list[str] = []
        self._tmp_pcap: str = ""
        self._tmp_result: str = ""
        self._disk_select_index = 0
        self._source_storage: IStorage | None = None
        self._destination_storage: IStorage | None = None
        self._gstreamer_state = GstreamerState()
        self._vehicles: Vehicles | None = None

    def _init_config(self) -> None:
        cfg = ProjectConfig.instance()
        self._disks = cfg.tmp_volumes
        self._tmp_pcap = cfg.tmp_pcap_path
        self._tmp_result = cfg.tmp_result_path

    def _init_runtime(self) -> None:
        self._vehicles = Vehicles.load(ProjectConfig.instance().vehicle_ids)
        self._source_storage = S3StorageFactory(S3StorageInfoFactory()).create_storage()
        self._source_storage.connect()
        self._destination_storage = S3StorageFactory(S3StorageInfoFactory()).create_storage()
        self._destination_storage.connect()

    def action(self) -> None:
        try:
            self._set_config()
            self._init_config()
            self._init_runtime()

            AppLogger.instance().info(f"[{self.name}] ExtractorModule start")

            # shared_queue[self.name] 을 직접 폴링 — JobRequest 만 받음 (single message type).
            job_queue = self._shared_queue[self.name]
            while not self.is_stop():
                try:
                    raw = job_queue.get_nowait()
                except Empty:
                    time.sleep(_POLL_INTERVAL_EMPTY)
                    continue
                self._handle_job_request(JobRequest.from_json(raw))

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

    # --- handler ---

    def _handle_job_request(self, packet: JobRequest) -> None:
        try:
            AppLogger.instance().info(f"JOB START -> Job ID : {packet.jobId}")

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

            ExtractRegistry.extract(packet.moduleType, ctx)

            job_complete = ProtocolMeta.instance().get_factory(E_PROTOCOL_ID.JOB_COMPLETE.value)(
                self.name, EXTRACTOR_MANAGER,
                packet.jobId, packet.vehicleId, packet.sensorType, packet.moduleType,
            )
            self.push_shared_job_queue(job_complete.to_json())
        except Exception as e:
            error_msg = (
                f"[{self.name}] Exception\n"
                f"Job Id : {packet.jobId}\n"
                f"Exception Time : {datetime.now()}\n"
                f"Message : {e}"
            )
            AppLogger.instance().exception(error_msg)
            error_noti = ProtocolMeta.instance().get_factory(E_PROTOCOL_ID.ERROR_NOTI.value)(
                self.name, EXTRACTOR_MANAGER,
                error_msg, packet.jobId, "UNKNOWN",
            )
            self.push_shared_job_queue(error_noti.to_json())

    def _get_tmp_saved_path(self) -> Tuple[str, str]:
        tmp_pcap_path = self._disks[self._disk_select_index] + self._tmp_pcap
        tmp_result_path = self._disks[self._disk_select_index] + self._tmp_result
        self._disk_select_index = (self._disk_select_index + 1) % len(self._disks)
        return tmp_pcap_path, tmp_result_path
