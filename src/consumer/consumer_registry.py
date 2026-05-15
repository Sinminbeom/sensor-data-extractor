from __future__ import annotations

from consumer.message_consumer import MessageConsumer
# 역할: 이름 → consumer 매핑 + 일괄 lifecycle 관리 (start/stop).
# 본 구현은 consumer 가 receive 만 책임 (send 는 process 가 직접 큐에 put).
class ConsumerRegistry:
    def __init__(self) -> None:
        self._consumers: dict[str, MessageConsumer] = {}

    def register(self, name: str, consumer: MessageConsumer) -> None:
        if name in self._consumers:
            raise KeyError(f"Consumer already registered: {name}")
        self._consumers[name] = consumer

    def start_all(self) -> None:
        for c in self._consumers.values():
            c.start()

    def stop_all(self) -> None:
        for c in self._consumers.values():
            c.stop()

    def get(self, name: str) -> MessageConsumer:
        return self._consumers[name]
