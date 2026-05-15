from __future__ import annotations

import time
from random import shuffle
from typing import Callable

from python_library.logger.app_logger import AppLogger
from python_library.storage.storage import IStorage
from python_library.thread.thread import abThread

from config.project_config import ProjectConfig
from config.storage_builder import StorageBuilder
from protocol.job_packet import JobPacket
from protocol.pk_ui_job_info import PkUiJobInfo
from sensor_category.enum_sensor import E_SENSOR_TYPE
from sensor_category.sensor_registry import E_CATE, SensorRegistry
from task.job_batch import JobBatch
from task.redis_job_list import RedisJobListStore
from task.task_registry import TaskRegistry
from task.task_tree import TaskTree
from task.vehicle_job_group import VehicleJobGroup
from utils.json_util import JsonUtil


class TaskRunner(abThread):
    """TaskRegistry lifecycle 컨트롤러 (자체가 task loop thread).

    TaskRegistry 가 sequence_id 매핑 + Redis 동기화만 담당하는 반면, 본 클래스는
    storage 에서 pcap 파일 walk → JobPacket 트리 구성 → worker dispatch → 완료 polling
    까지 한 task 의 전체 사이클을 관리한다.
    """

    SENDER_NAME = "TaskRunner"
    POLL_INTERVAL_IDLE = 0.1

    def __init__(
        self,
        slack_message_sender,
        redis_job_list_store: RedisJobListStore,
        assign_job_lambda: Callable[[JobPacket], None],
    ) -> None:
        super().__init__()
        self._registry = TaskRegistry(redis_job_list_store)
        self._source_storage: IStorage
        self._source_storage, self._source_root = StorageBuilder.build_source()
        _, self._destination_root = StorageBuilder.build_destination()

        self._slack_message_sender = slack_message_sender

        self._config = ProjectConfig.instance()
        self._download_path = self._source_root
        self._upload_path = self._destination_root
        self._assign_job = assign_job_lambda

        self._init()

    def _init(self) -> None:
        SensorRegistry.instance().initialize()
        SensorRegistry.instance().register_sensor()
        SensorRegistry.instance().register_module()

    def push(self, task_job) -> str:
        return self._registry.push(task_job)

    def delete(self, task_job) -> None:
        self._registry.delete(task_job)

    def complete(self, vehicle_id: str, job_id: str) -> None:
        self._registry.complete(vehicle_id, job_id)

    # --- task loop (abThread.action 본체) ---

    def action(self) -> None:
        while True:
            seq, task_tree = self._wait_for_next_task()
            self._populate_task(seq, task_tree)
            self._assign_all_jobs(task_tree)
            self._wait_until_complete(task_tree)
            self._finalize_task()

    def _wait_for_next_task(self) -> tuple[str, TaskTree]:
        """레지스트리가 비어있으면 sleep, 들어오면 첫 entry 반환."""
        while True:
            pick = self._registry.pick()
            if pick is not None:
                return pick
            time.sleep(TaskRunner.POLL_INTERVAL_IDLE)

    def _populate_task(self, seq: str, task_tree: TaskTree) -> None:
        """vehicle_id 가 ALL 이면 모든 차량, 아니면 단일 차량을 walk 해서 잡 등록."""
        date = task_tree.date
        vehicle_id = task_tree.vehicle_id
        vehicle_jobs = VehicleJobGroup()
        if vehicle_id == E_SENSOR_TYPE.ALL:
            for v_id in self._list_immediate_subdirs(self._download_path):
                self._build_job_batch(vehicle_jobs, v_id, date, seq)
        else:
            self._build_job_batch(vehicle_jobs, vehicle_id, date, seq)
        task_tree.set_vehicle_jobs(vehicle_jobs)

    def _build_job_batch(
        self,
        vehicle_jobs: VehicleJobGroup,
        vehicle_id: str,
        date: str,
        seq: str,
    ) -> None:
        batch = JobBatch()
        sensor_types = SensorRegistry.instance().get_cate2_list(E_CATE.SENSOR_TYPE)

        for sensor_type in sensor_types:
            sensor_type_lower = sensor_type.lower()
            sensor_names = SensorRegistry.instance().get_sensor_name_list(
                E_CATE.SENSOR_TYPE, sensor_type
            )
            for sensor_name in sensor_names:
                sensor_name_lower = sensor_name.lower()
                path = (
                    f"{self._download_path}/{vehicle_id}/{sensor_type_lower}/"
                    f"{sensor_name_lower}/{date}"
                )

                module_type = SensorRegistry.instance().get_cate2_by_value(
                    E_CATE.MODULE_TYPE, sensor_name
                )
                if module_type not in self._config.module_types:
                    continue
                if sensor_name_lower not in self._config.sensor_names:
                    continue

                if not self._source_storage.is_exists(path):
                    continue
                for sf in self._source_storage.get_file_list(path):
                    if sf.is_dir():
                        continue
                    pcap_path = sf.get_file_path()
                    file_name = sf.get_file_name()
                    job_id = f"{seq}_{file_name}"
                    batch.add(
                        JobPacket(
                            TaskRunner.SENDER_NAME,
                            job_id,
                            vehicle_id,
                            sensor_type,
                            module_type,
                            pcap_path,
                            self._upload_path,
                        )
                    )
        vehicle_jobs.add_batch(vehicle_id, batch)

    def _list_immediate_subdirs(self, path: str) -> list[str]:
        # python-library IStorage 는 디렉터리 entry 를 직접 반환하지 않으므로,
        # 재귀 file list 에서 path 바로 다음 segment 를 set 으로 추출.
        prefix = path.rstrip("/") + "/"
        names: set[str] = set()
        for sf in self._source_storage.get_file_list(path):
            full = sf.get_file_path()
            if not full.startswith(prefix):
                continue
            tail = full[len(prefix):]
            first = tail.split("/", 1)[0]
            if first:
                names.add(first)
        return sorted(names)

    def _assign_all_jobs(self, task_tree: TaskTree) -> None:
        # 트리 전체 traversal 후 워커 분산을 위해 shuffle.
        # Composite traversal 결과를 caller 에서 셔플하는 게 패턴 정합성에 맞음.
        jobs = list(task_tree.iter_jobs())
        shuffle(jobs)
        for job in jobs:
            self._assign_job(job)

    def _wait_until_complete(self, task_tree: TaskTree) -> None:
        while not task_tree.is_complete():
            time.sleep(TaskRunner.POLL_INTERVAL_IDLE)

    def _finalize_task(self) -> None:
        success_json = self._registry.pop()
        if success_json is None:
            return
        success = JsonUtil.from_json(success_json, PkUiJobInfo)
        AppLogger.instance().info(
            f"[{TaskRunner.SENDER_NAME}] Success\n"
            f"Date : {success.get_date()}\n"
            f"VehicleId : {success.get_vehicle_id()}\n"
            f"SequenceId : {success.get_sequence_id()}"
        )
