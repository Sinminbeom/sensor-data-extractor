from __future__ import annotations

import atexit
from collections import deque

from config.project_config import ProjectConfig
from define.process_name import EXTRACTOR_MANAGER, WEB_SERVICE
from protocol.pk_ui_job import PkUiJob
from protocol.pk_ui_job_delete import PkUiJobDelete
from protocol.protocol_meta import E_PROTOCOL_ID, ProtocolMeta
from protocol.protocol_utils import ProtocolUtils
from task.redis_job_list import RedisJobListStore
from task.task_tree import TaskTree
from utils.json_util import JsonUtil


class TaskRegistry:
    """잡 sequence_id 별 TaskTree 순서 컨테이너.

    Composite 트리(TaskTree → JobBatch) 의 root 들을 FIFO 로
    묶고, Redis JOB_LIST_QUEUE 와 동기화해 영속화한다. Redis 접근은 RedisJobListStore 에
    위임 — 본 클래스는 deque + Store 호출만 담당.
    """

    def __init__(self, job_list_store: RedisJobListStore) -> None:
        self._queue: deque[tuple[str, TaskTree]] = deque()
        self._store = job_list_store
        self._config = ProjectConfig.instance()
        self._init()

    def _init(self) -> None:
        self.clear()

        def exit_handler() -> None:
            try:
                self.clear()
            except Exception:
                pass

        atexit.register(exit_handler)

    def push(self, task_job: PkUiJob) -> str:
        seq = ProtocolUtils.instance().get_sequence_id_now()
        task_tree = TaskTree(task_job.date, task_job.vehicleId)
        info = ProtocolMeta.instance().get_factory(E_PROTOCOL_ID.UI_JOB_LIST.value)(
            EXTRACTOR_MANAGER, WEB_SERVICE,
            task_job.date, task_job.vehicleId, seq,
        )
        self._queue.append((seq, task_tree))
        self._store.push(JsonUtil.to_json(info))
        return seq

    def pop(self) -> str | None:
        if self.is_empty():
            return None
        self._queue.popleft()
        return self._store.pop()

    def pick(self) -> tuple[str, TaskTree] | None:
        if self.is_empty():
            return None
        return self._queue[0]

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def delete(self, task_job: PkUiJobDelete) -> None:
        target_seq = task_job.sequenceId
        for index, (seq, task_tree) in enumerate(self._queue):
            if seq != target_seq:
                continue

            if not task_tree.is_populated():
                del self._queue[index]
            else:
                task_tree.clear()

            delete_info = ProtocolMeta.instance().get_factory(E_PROTOCOL_ID.UI_JOB_LIST.value)(
                EXTRACTOR_MANAGER, WEB_SERVICE,
                task_tree.date, task_tree.vehicle_id, seq,
            )
            self._store.delete(JsonUtil.to_json(delete_info))
            return

    def complete(self, vehicle_id: str, job_id: str) -> None:
        # job_id format = "{seq}_{file_name}" where seq = "YYYYMMDDHHMMSS_NNNNNNNN".
        target_seq = "_".join(job_id.split("_")[:2])
        for seq, task_tree in self._queue:
            if seq == target_seq:
                task_tree.complete_job(vehicle_id, job_id)
                return

    def clear(self) -> None:
        self._store.clear()
