from dataclasses import dataclass

from protocol.message import abMessage
# UI에서 발행하는 잡 삭제 요청 packet (sequenceId 기준 삭제).
@dataclass(kw_only=True)
class PkUiJobDelete(abMessage):
    sequenceId: str
# Jenkins build name 문자열에서 PkUiJobDelete 생성. token = "{date}_{vehicle}_{ts}_{seq}".
class PkUiJobDeleteHelper:
    @staticmethod
    def factory_jenkins_from(str_mark_message: str) -> PkUiJobDelete:
        from define.process_name import EXTRACTOR_MANAGER, WEB_SERVICE
        from protocol.protocol_meta import E_PROTOCOL_ID, ProtocolMeta
        tokens = str_mark_message.split("_")
        sequence_id = tokens[2] + "_" + tokens[3]
        return ProtocolMeta.instance().get_factory(E_PROTOCOL_ID.UI_JOB_DELETE.value)(
            WEB_SERVICE, EXTRACTOR_MANAGER,
            sequence_id,
        )
