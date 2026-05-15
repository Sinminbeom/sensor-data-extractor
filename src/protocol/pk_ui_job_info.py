from dataclasses import dataclass

from protocol.pk_ui_job import PkUiJob
# 잡 큐 목록 조회 시 응답 packet — sequenceId 추가.
@dataclass
class PkUiJobInfo(PkUiJob):
    sequenceId: str = ""

    def __init__(
        self,
        protocol_id: str = "",
        sender: str = "",
        date: str = "",
        vehicle_id: str = "",
        sequence_id: str = "",
    ) -> None:
        super().__init__(protocol_id, sender, date, vehicle_id)
        self.sequenceId = sequence_id

    def get_sequence_id(self) -> str:
        return self.sequenceId
