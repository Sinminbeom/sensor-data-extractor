from dataclasses import dataclass

from protocol.base_protocol import BaseProtocol
from protocol.message_noti import MessageNoti
# 잡 처리 실패 시 ExtractorWorker가 발행하는 에러 packet.
@dataclass
class ErrorNoti(MessageNoti):
    errorType: str = ""
    jobId: str = ""

    def __init__(self, sender: str, comment: str, job_id: str, error_type: str) -> None:
        from protocol.protocol_meta import ProtocolMeta
        BaseProtocol.__init__(self, ProtocolMeta.E_PROTOCOL_ID.ERROR_NOTI, sender)
        self.comment = comment
        self.jobId = job_id
        self.errorType = error_type

    def get_job_id(self) -> str:
        return self.jobId

    def get_error_type(self) -> str:
        return self.errorType
