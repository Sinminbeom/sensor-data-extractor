from dataclasses import dataclass

from protocol.message import abMessage
# 일반 알림 packet — comment 필드 보유. 슬랙 알림 등에 사용.
@dataclass(kw_only=True)
class MessageNoti(abMessage):
    comment: str
