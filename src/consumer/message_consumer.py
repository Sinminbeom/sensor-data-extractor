from __future__ import annotations

import time
from queue import Empty, Queue
from threading import Lock
from typing import Any, Callable

from python_library.thread.thread import abThreading
# 역할: 단일 큐를 watch 하면서 메시지가 들어오면 callback 으로 dispatch (consumer 패턴).
# 클래스명 cMessageHandler → MessageConsumer. PascalCase 메서드 모두 snake_case.
#
# Consumer 는 RECV 큐 1 개에 대해서만 polling 책임 (단일 의도).
class MessageConsumer(abThreading):
    POLL_INTERVAL_EMPTY = 0.1
    POLL_INTERVAL_BUSY = 0.0

    def __init__(self, queue: Queue, on_message: Callable[[Any], None]) -> None:
        super().__init__()
        self._queue = queue
        self._on_message = on_message
        self._lock = Lock()
        self._is_running = False

    def start(self) -> None:
        if self._is_running:
            return
        super().start()  # abThread.start (Thread.start 호출)
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False
        super().stop()

    def action(self) -> None:
        while self._is_running:
            msg = self._pop()
            if msg is None:
                time.sleep(MessageConsumer.POLL_INTERVAL_EMPTY)
                continue
            self._on_message(msg)
            time.sleep(MessageConsumer.POLL_INTERVAL_BUSY)

    def _pop(self) -> Any | None:
        with self._lock:
            try:
                return self._queue.get_nowait()
            except Empty:
                return None
