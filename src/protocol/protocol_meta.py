"""protocol_id → (factory + decoder + receive_handlers + extractors) 매핑 레지스트리.

replayer 패턴(ProtocolEntry dataclass + table dict + 정적 메서드 registry).
- factory: packet dataclass instance 생성 lambda
- decoder: json 문자열 → packet (jsons.loads)
- receive_handlers: receiver(E_RECEIVER) → ProtocolHandler staticmethod 매핑
- extractors: module_type → 추출기 callable (JOB_REQUEST 만 채워짐)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, ClassVar, Dict, Mapping

import jsons

from python_library.define.enum import IENUM
from python_library.process.process import IProcess

from protocol.base_protocol import BaseProtocol

ReceiverKey = Any
FactoryFn = Callable[..., BaseProtocol]
DecoderFn = Callable[[str], BaseProtocol]
HandlerFn = Callable[[IProcess, BaseProtocol], Any]
ExtractFn = Callable[[Any], None]  # (ExtractContext) -> None — Any 로 두어 순환 import 회피
# replayer 패턴으로 Enum 격상.
class E_PROTOCOL_ID(Enum):
    UI_JOB_REQUEST = "UI_JOB_REQUEST"
    UI_JOB_DELETE = "UI_JOB_DELETE"
    UI_JOB_LIST = "UI_JOB_LIST"
    JOB_REQUEST = "JOB_REQUEST"
    JOB_COMPLETE = "JOB_COMPLETE"
    ERROR_NOTI = "ERROR_NOTI"
    MESSAGE_NOTI = "MESSAGE_NOTI"

# receiver 식별자. process_category 의 E_CATE 와는 별도 — 같은 EXTRACTOR 카테고리 안에서도
# manager(ExtractorManager) 와 worker(ExtractorWorker) 가 서로 다른 protocol_id 를 받기 때문.
class E_RECEIVER(IENUM):
    EXTRACTOR_WORKER = "EXTRACTOR_WORKER"
    EXTRACTOR_MANAGER = "EXTRACTOR_MANAGER"
    WEB_SERVICE = "WEB_SERVICE"

@dataclass(frozen=True)
class ProtocolEntry:
    factory: FactoryFn
    decoder: DecoderFn
    receive_handlers: Mapping[ReceiverKey, HandlerFn] = field(default_factory=dict)
    extractors: Mapping[str, ExtractFn] = field(default_factory=dict)

class ProtocolMeta:
    """Static-style registry.

    Usage:
        ProtocolMeta.initialize()  # idempotent
        handler = ProtocolMeta.get_receive_handler(E_PROTOCOL_ID.JOB_REQUEST, E_RECEIVER.EXTRACTOR_WORKER)
        handler(worker, packet)
        # JOB_REQUEST 만 추가로 module_type sub-dispatch
        extract_fn = ProtocolMeta.get_extractor(E_PROTOCOL_ID.JOB_REQUEST, module_type)
        extract_fn(ctx)
    """

    table: ClassVar[Dict[E_PROTOCOL_ID, ProtocolEntry]] = {}
    _initialized: ClassVar[bool] = False

    # ---------------------------
    # Initialization
    # ---------------------------
    @classmethod
    def initialize(cls) -> None:
        if cls._initialized:
            return
        cls._register_protocols()
        cls._initialized = True

    @classmethod
    def _register(cls, protocol_id: E_PROTOCOL_ID, entry: ProtocolEntry) -> None:
        if protocol_id in cls.table:
            raise KeyError(f"Protocol already registered: {protocol_id}")
        cls.table[protocol_id] = entry

    @classmethod
    def _register_protocols(cls) -> None:
        # 지연 import (callback handler 안에서 protocol 클래스를 다시 참조하므로 circular 회피)
        from define.module_type import E_MODULE_TYPE
        from extractor.sensors.am20_extract import Am20Extract
        from extractor.sensors.at128_extract import At128Extract
        from extractor.sensors.gnss_extract import GnssExtract
        from extractor.sensors.imu_extract import ImuExtract
        from extractor.sensors.rsbp_extract import RsbpExtract
        from protocol.error_noti import ErrorNoti
        from protocol.job_complete import JobComplete
        from protocol.job_packet import JobPacket
        from protocol.pk_ui_job import PkUiJob
        from protocol.pk_ui_job_delete import PkUiJobDelete
        from protocol.protocol_handler import ProtocolHandler

        # ===== UI_JOB_REQUEST → MANAGER =====
        cls._register(
            E_PROTOCOL_ID.UI_JOB_REQUEST,
            ProtocolEntry(
                factory=lambda sender, date, vehicle_id: PkUiJob(
                    E_PROTOCOL_ID.UI_JOB_REQUEST.value, sender, date, vehicle_id
                ),
                decoder=lambda raw: jsons.loads(raw, cls=PkUiJob),
                receive_handlers={
                    E_RECEIVER.EXTRACTOR_MANAGER: ProtocolHandler.manager_ui_job_request,
                },
            ),
        )

        # ===== UI_JOB_DELETE → MANAGER =====
        cls._register(
            E_PROTOCOL_ID.UI_JOB_DELETE,
            ProtocolEntry(
                factory=lambda sender, sequence_id: PkUiJobDelete(
                    E_PROTOCOL_ID.UI_JOB_DELETE.value, sender, sequence_id
                ),
                decoder=lambda raw: jsons.loads(raw, cls=PkUiJobDelete),
                receive_handlers={
                    E_RECEIVER.EXTRACTOR_MANAGER: ProtocolHandler.manager_ui_job_delete,
                },
            ),
        )

        # ===== JOB_REQUEST → WORKER (module_type 별 추출기 sub-dispatch 포함) =====
        cls._register(
            E_PROTOCOL_ID.JOB_REQUEST,
            ProtocolEntry(
                factory=lambda sender, job_id, vehicle_id, sensor_type, module_type, src_path, dst_path: JobPacket(
                    sender, job_id, vehicle_id, sensor_type, module_type, src_path, dst_path
                ),
                decoder=lambda raw: jsons.loads(raw, cls=JobPacket),
                receive_handlers={
                    E_RECEIVER.EXTRACTOR_WORKER: ProtocolHandler.worker_job_request,
                },
                extractors={
                    E_MODULE_TYPE.AT128: At128Extract.extract,
                    E_MODULE_TYPE.RSBP: RsbpExtract.extract,
                    E_MODULE_TYPE.AM20: Am20Extract.extract,
                    E_MODULE_TYPE.GNSS: GnssExtract.extract,
                    E_MODULE_TYPE.IMU: ImuExtract.extract,
                },
            ),
        )

        # ===== JOB_COMPLETE → MANAGER =====
        cls._register(
            E_PROTOCOL_ID.JOB_COMPLETE,
            ProtocolEntry(
                factory=lambda sender, job_id, vehicle_id, sensor_type, module_type: JobComplete(
                    sender, job_id, vehicle_id, sensor_type, module_type
                ),
                decoder=lambda raw: jsons.loads(raw, cls=JobComplete),
                receive_handlers={
                    E_RECEIVER.EXTRACTOR_MANAGER: ProtocolHandler.manager_job_complete,
                },
            ),
        )

        # ===== ERROR_NOTI → MANAGER =====
        cls._register(
            E_PROTOCOL_ID.ERROR_NOTI,
            ProtocolEntry(
                factory=lambda sender, comment, job_id, error_type: ErrorNoti(
                    sender, comment, job_id, error_type
                ),
                decoder=lambda raw: jsons.loads(raw, cls=ErrorNoti),
                receive_handlers={
                    E_RECEIVER.EXTRACTOR_MANAGER: ProtocolHandler.manager_error_noti,
                },
            ),
        )

    # ---------------------------
    # Conversion helper
    # ---------------------------
    @classmethod
    def _to_enum(cls, protocol_id: E_PROTOCOL_ID | str) -> E_PROTOCOL_ID:
        if isinstance(protocol_id, E_PROTOCOL_ID):
            return protocol_id
        try:
            return E_PROTOCOL_ID(protocol_id)
        except ValueError as e:
            raise KeyError(f"Unknown protocol_id: {protocol_id}") from e

    # ---------------------------
    # Public API
    # ---------------------------
    @classmethod
    def get_receive_handler(
        cls, protocol_id: E_PROTOCOL_ID | str, receiver: ReceiverKey
    ) -> HandlerFn:
        cls.initialize()
        pid = cls._to_enum(protocol_id)
        return cls.table[pid].receive_handlers[receiver]

    @classmethod
    def get_protocol_factory(cls, protocol_id: E_PROTOCOL_ID | str) -> FactoryFn:
        cls.initialize()
        return cls.table[cls._to_enum(protocol_id)].factory

    @classmethod
    def get_json_decoder(cls, protocol_id: E_PROTOCOL_ID | str) -> DecoderFn:
        cls.initialize()
        return cls.table[cls._to_enum(protocol_id)].decoder

    @classmethod
    def get_extractor(
        cls, protocol_id: E_PROTOCOL_ID | str, module_type: str
    ) -> ExtractFn:
        cls.initialize()
        return cls.table[cls._to_enum(protocol_id)].extractors[module_type]
