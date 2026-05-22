from dataclasses import dataclass

from protocol.message_noti import MessageNoti
# 잡 처리 실패 시 ExtractorModule가 발행하는 에러 packet.
@dataclass(kw_only=True)
class ErrorNoti(MessageNoti):
    errorType: str
    jobId: str
