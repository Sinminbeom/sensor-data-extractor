from dataclasses import dataclass

from protocol.base_protocol import BaseProtocol
# UI에서 발행하는 잡 삭제 요청 packet (sequenceId 기준 삭제).
@dataclass
class PkUiJobDelete(BaseProtocol):
    sequenceId: str = ""

    def __init__(self, protocol_id: str = "", sender: str = "", sequence_id: str = "") -> None:
        super().__init__(protocol_id, sender)
        self.sequenceId = sequence_id

    def get_sequence_id(self) -> str:
        return self.sequenceId
# Jenkins build name 문자열에서 PkUiJobDelete 생성. token = "{date}_{vehicle}_{ts}_{seq}".
class PkUiJobDeleteHelper:
    @staticmethod
    def factory_jenkins_from(str_mark_message: str) -> PkUiJobDelete:
        from protocol.protocol_meta import ProtocolMeta
        tokens = str_mark_message.split("_")
        sequence_id = tokens[2] + "_" + tokens[3]
        return PkUiJobDelete(ProtocolMeta.E_PROTOCOL_ID.UI_JOB_DELETE, "UI", sequence_id)
    @staticmethod
    def factory_jenkins_from(str_mark_message: str) -> PkUiJobDelete:
        return PkUiJobDeleteHelper.factory_jenkins_from(str_mark_message)
