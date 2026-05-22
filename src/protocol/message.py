from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self


class IMessage(ABC):
    """직렬화 contract. 모든 message/packet 은 to_json / from_json 보유."""

    @abstractmethod
    def to_json(self) -> str: ...

    @classmethod
    @abstractmethod
    def from_json(cls, json_string: str) -> Self: ...


@dataclass
class abMessage(IMessage):
    """모든 protocol packet base — protocolId / sender / receiver 공통 필드.

    실제 직렬화는 ProtocolMeta.to_json / from_json 에 위임 (사이클 회피 위해 lazy import).
    """

    protocolId: str
    sender: str
    receiver: str

    def to_json(self) -> str:
        from protocol.protocol_meta import ProtocolMeta

        return ProtocolMeta.to_json(self)

    @classmethod
    def from_json(cls, json_string: str) -> Self:
        from protocol.protocol_meta import ProtocolMeta

        return ProtocolMeta.from_json(cls, json_string)
