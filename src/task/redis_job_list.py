from __future__ import annotations

import redis

from config.redis_config import RedisConfig
from protocol.pk_ui_job_info import PkUiJobInfo
from utils.json_util import JsonUtil


class RedisJobListStore:
    def __init__(self, config: RedisConfig | None = None) -> None:
        self._config = config or RedisConfig()
        self._client: redis.Redis | None = None

    def connect(self) -> None:
        if self._client is not None:
            return
        self._client = redis.Redis(
            host=self._config.ip,
            port=self._config.port,
            decode_responses=True,
        )

    def disconnect(self) -> None:
        if self._client is None:
            return
        try:
            self._client.close()
        except Exception:
            pass
        self._client = None

    def _queue_name(self, mode: str | None = None) -> str:
        return self._config.job_list_queue_with_mode(mode)

    def _client_or_connect(self) -> redis.Redis:
        if self._client is None:
            self.connect()
        assert self._client is not None
        return self._client

    # --- queue ops (TaskRegistry 가 직접 사용) ---

    def push(self, json_message: str) -> None:
        self._client_or_connect().lpush(self._queue_name(), json_message)

    def pop(self) -> str | None:
        return self._client_or_connect().rpop(self._queue_name())

    def delete(self, json_message: str) -> None:
        self._client_or_connect().lrem(self._queue_name(), 1, json_message)

    def size(self) -> int:
        return int(self._client_or_connect().llen(self._queue_name()))

    def clear(self) -> None:
        client = self._client_or_connect()
        name = self._queue_name()
        # rpop 으로 모두 비우기 (lrange + del 대신 atomic delete 가 더 빠르지만 PopBulk 호환 위해 유지)
        while client.rpop(name) is not None:
            pass

    # --- read-only queries (Web Service 가 사용) ---

    def fetch_all(self, mode: str | None = None) -> list[str]:
        client = self._client_or_connect()
        name = self._queue_name(mode)
        length = client.llen(name)
        if length <= 0:
            return []
        return list(client.lrange(name, 0, length - 1))

    def fetch_all_as_jenkins_names(self, mode: str | None = None) -> list[str]:
        result: list[str] = []
        for raw in self.fetch_all(mode):
            obj = JsonUtil.from_json(raw, PkUiJobInfo)
            result.append(f"{obj.date}_{obj.vehicleId}_{obj.sequenceId}")
        return result
