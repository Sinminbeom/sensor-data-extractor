from __future__ import annotations

import time
from queue import Empty, Queue
from typing import Any, Callable

from consumer.message_consumer import MessageConsumer
# 단일 메시지 대신 큐 안의 메시지 list 를 한 번에 pop 해 bulk 로 callback 에 전달.
# multi-process 환경에서 worker → manager 회신을 bulk consume 할 때 유용.
class BulkMessageConsumer(MessageConsumer):
    def __init__(self, queue: Queue, on_bulk: Callable[[list[Any]], None]) -> None:
        super().__init__(queue, on_bulk)  # on_message 자리에 on_bulk 주입

    def action(self) -> None:
        while self._is_running:
            bulk = self._pop_bulk()
            if not bulk:
                time.sleep(MessageConsumer.POLL_INTERVAL_EMPTY)
                continue
            self._on_message(bulk)
            time.sleep(MessageConsumer.POLL_INTERVAL_BUSY)

    def _pop_bulk(self) -> list[Any]:
        result: list[Any] = []
        with self._lock:
            while True:
                try:
                    result.append(self._queue.get_nowait())
                except Empty:
                    break
        return result
