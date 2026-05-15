from dataclasses import dataclass

from protocol.base_protocol import BaseProtocol
# 일반 알림 packet — comment 필드 보유. 슬랙 알림 등에 사용.
@dataclass
class MessageNoti(BaseProtocol):
    comment: str = ""

    def __init__(self, sender: str, comment: str) -> None:
        from protocol.protocol_meta import ProtocolMeta
        super().__init__(ProtocolMeta.E_PROTOCOL_ID.MESSAGE_NOTI, sender)
        self.comment = comment

    def get_comment(self) -> str:
        return self.comment
