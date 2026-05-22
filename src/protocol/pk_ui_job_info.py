from dataclasses import dataclass

from protocol.pk_ui_job import PkUiJob
# 잡 큐 목록 조회 시 응답 packet — sequenceId 추가.
@dataclass(kw_only=True)
class PkUiJobInfo(PkUiJob):
    sequenceId: str
