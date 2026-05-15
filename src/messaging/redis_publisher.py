from __future__ import annotations

import redis

from config.redis_config import RedisConfig
# COM_QUEUE 에 잡 요청/삭제 메시지를 lpush 발행. Web Service 측이 사용.
#
# 책임을 큐별 / 동작별로 분리:
#   - RedisPublisher  : COM_QUEUE lpush          (Web → Manager)
#   - RedisSubscriber : COM_QUEUE rpop           (Manager 측 thread, messaging/)
#   - RedisJobListStore: JOB_LIST_QUEUE 영속화   (TaskRegistry 가 사용, task/)
class RedisPublisher:
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

    def publish(self, json_message: str, mode: str | None = None) -> None:
        if self._client is None:
            self.connect()
        assert self._client is not None
        self._client.lpush(self._config.com_queue_with_mode(mode), json_message)
