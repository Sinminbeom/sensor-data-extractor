"""receive handler 라우팅 테이블.

ProtocolMeta 의 receive_handlers 에 등록되는 staticmethod 모음. 각 staticmethod 는
(process, packet) 시그니처를 받아 isinstance 확인 후 process 의 handle_xxx_* 로 위임.
"""
from __future__ import annotations

from python_library.process.process import IProcess

from protocol.base_protocol import BaseProtocol


class ProtocolHandler:
    # ============================================================
    # EXTRACTOR_WORKER — 잡 요청 수신
    # ============================================================
    @staticmethod
    def worker_job_request(process: IProcess, packet: BaseProtocol) -> None:
        from app.extractor.process.worker.worker import ExtractorWorker
        from protocol.job_packet import JobPacket
        assert isinstance(process, ExtractorWorker)
        assert isinstance(packet, JobPacket)
        process.handle_job_request(packet)

    # ============================================================
    # EXTRACTOR_MANAGER — worker → manager 회신 + UI 요청
    # ============================================================
    @staticmethod
    def manager_job_complete(process: IProcess, packet: BaseProtocol) -> None:
        from app.extractor.process.manager.manager import ExtractorManager
        from protocol.job_complete import JobComplete
        assert isinstance(process, ExtractorManager)
        assert isinstance(packet, JobComplete)
        process.handle_job_complete(packet)

    @staticmethod
    def manager_error_noti(process: IProcess, packet: BaseProtocol) -> None:
        from app.extractor.process.manager.manager import ExtractorManager
        from protocol.error_noti import ErrorNoti
        assert isinstance(process, ExtractorManager)
        assert isinstance(packet, ErrorNoti)
        process.handle_error_noti(packet)

    @staticmethod
    def manager_ui_job_request(process: IProcess, packet: BaseProtocol) -> None:
        from app.extractor.process.manager.manager import ExtractorManager
        from protocol.pk_ui_job import PkUiJob
        assert isinstance(process, ExtractorManager)
        assert isinstance(packet, PkUiJob)
        process.handle_ui_job_request(packet)

    @staticmethod
    def manager_ui_job_delete(process: IProcess, packet: BaseProtocol) -> None:
        from app.extractor.process.manager.manager import ExtractorManager
        from protocol.pk_ui_job_delete import PkUiJobDelete
        assert isinstance(process, ExtractorManager)
        assert isinstance(packet, PkUiJobDelete)
        process.handle_ui_job_delete(packet)
