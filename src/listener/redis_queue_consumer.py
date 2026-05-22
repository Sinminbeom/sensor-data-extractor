from __future__ import annotations

import time
from typing import Callable

import redis

from python_library.logger.app_logger import AppLogger
from python_library.thread.thread import abThreading

from config.redis_config import RedisConfig
# Redis COM_QUEUE consumer. 큐 추상화(ICollection) 를 걷어내고 redis-py 직접 사용.
#
# 책임: 별도 thread 에서 COM_QUEUE 의 모든 메시지를 한 번에 pop (rpop loop) 해서 callback 으로 전달.
#
# 큐 분리 정리:
#   - RedisQueueProducer : COM_QUEUE lpush                       (Web → Manager)
#   - RedisQueueConsumer : COM_QUEUE rpop (본 클래스)            (Manager 측 thread)
#   - RedisJobListStore  : JOB_LIST_QUEUE 영속화                 (task/redis_job_list.py)
class RedisQueueConsumer(abThreading):
    POLL_INTERVAL_EMPTY = 0.1
    POLL_INTERVAL_BUSY = 0.0

    def __init__(
        self,
        on_bulk: Callable[[list[str]], None],
        config: RedisConfig | None = None,
    ) -> None:
        super().__init__()
        self._config = config or RedisConfig()
        self._on_bulk = on_bulk
        self._is_running = False
        self._client: redis.Redis | None = None

    def start(self) -> None:
        if self._is_running:
            return
        self._client = redis.Redis(
            host=self._config.ip, port=self._config.port, decode_responses=True
        )
        super().start()  # abThread.start
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False
        super().stop()
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

    def action(self) -> None:
        while self._is_running:
            bulk = self._pop_all()
            if not bulk:
                time.sleep(RedisQueueConsumer.POLL_INTERVAL_EMPTY)
                continue
            try:
                self._on_bulk(bulk)
            except Exception as e:
                AppLogger.instance().exception(f"RedisQueueConsumer callback failed: {e}")
            time.sleep(RedisQueueConsumer.POLL_INTERVAL_BUSY)

    def _pop_all(self) -> list[str]:
        # 단일 consumer 가정 — atomic 보장 안 됨 (multi consumer 시 race).
        assert self._client is not None
        name = self._config.com_queue_with_mode(None)
        size = self._client.llen(name)
        if size == 0:
            return []
        result: list[str] = []
        for _ in range(size):
            v = self._client.rpop(name)
            if v is None:
                break
            result.append(v)
        return result
