"""protocol_id → ProtocolEntry(decoder, factory) registry + JSON 직렬화 helper.

ProtocolMeta 가 protocol 관련 모든 책임 담당:
  - registry   : protocolId → ProtocolEntry lookup
  - decoder    : raw json → typed abMessage (decode_body)
  - factory    : protocolId / receiver 등 고정 필드 숨긴 객체 생성자
  - serializer : abMessage ↔ JSON (to_json / from_json static)
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Type, TypeVar

from python_library.singleton.singleton import Singleton

from protocol.message import abMessage

T = TypeVar("T")
_DecoderFn = Callable[[str], abMessage]
_FactoryFn = Callable[..., abMessage]


class E_PROTOCOL_ID(Enum):
    UI_JOB_REQUEST = "UI_JOB_REQUEST"
    UI_JOB_DELETE = "UI_JOB_DELETE"
    UI_JOB_LIST = "UI_JOB_LIST"
    JOB_REQUEST = "JOB_REQUEST"
    JOB_COMPLETE = "JOB_COMPLETE"
    ERROR_NOTI = "ERROR_NOTI"
    MESSAGE_NOTI = "MESSAGE_NOTI"


@dataclass(frozen=True)
class ProtocolEntry:
    decoder: _DecoderFn
    factory: _FactoryFn


class ProtocolMeta(Singleton):
    def __init__(self) -> None:
        super().__init__()
        self._entries: dict[str, ProtocolEntry] = {}
        self._register_protocols()

    def _register_protocols(self) -> None:
        # 사이클 회피용 lazy import.
        from protocol.error_noti import ErrorNoti
        from protocol.job_complete import JobComplete
        from protocol.job_request import JobRequest
        from protocol.message_noti import MessageNoti
        from protocol.pk_ui_job import PkUiJob
        from protocol.pk_ui_job_delete import PkUiJobDelete
        from protocol.pk_ui_job_info import PkUiJobInfo

        self._register(
            E_PROTOCOL_ID.UI_JOB_REQUEST.value,
            decoder=lambda raw: ProtocolMeta.from_json(PkUiJob, raw),
            factory=lambda sender, receiver, date, vehicle_id: PkUiJob(
                protocolId=E_PROTOCOL_ID.UI_JOB_REQUEST.value,
                sender=sender,
                receiver=receiver,
                date=date,
                vehicleId=vehicle_id,
            ),
        )
        self._register(
            E_PROTOCOL_ID.UI_JOB_DELETE.value,
            decoder=lambda raw: ProtocolMeta.from_json(PkUiJobDelete, raw),
            factory=lambda sender, receiver, sequence_id: PkUiJobDelete(
                protocolId=E_PROTOCOL_ID.UI_JOB_DELETE.value,
                sender=sender,
                receiver=receiver,
                sequenceId=sequence_id,
            ),
        )
        self._register(
            E_PROTOCOL_ID.UI_JOB_LIST.value,
            decoder=lambda raw: ProtocolMeta.from_json(PkUiJobInfo, raw),
            factory=lambda sender, receiver, date, vehicle_id, sequence_id: PkUiJobInfo(
                protocolId=E_PROTOCOL_ID.UI_JOB_LIST.value,
                sender=sender,
                receiver=receiver,
                date=date,
                vehicleId=vehicle_id,
                sequenceId=sequence_id,
            ),
        )
        self._register(
            E_PROTOCOL_ID.JOB_REQUEST.value,
            decoder=lambda raw: ProtocolMeta.from_json(JobRequest, raw),
            factory=lambda sender, receiver, job_id, vehicle_id, sensor_type, module_type, src_path, dst_path: JobRequest(
                protocolId=E_PROTOCOL_ID.JOB_REQUEST.value,
                sender=sender,
                receiver=receiver,
                jobId=job_id,
                vehicleId=vehicle_id,
                sensorType=sensor_type,
                moduleType=module_type,
                srcPath=src_path,
                dstPath=dst_path,
            ),
        )
        self._register(
            E_PROTOCOL_ID.JOB_COMPLETE.value,
            decoder=lambda raw: ProtocolMeta.from_json(JobComplete, raw),
            factory=lambda sender, receiver, job_id, vehicle_id, sensor_type, module_type: JobComplete(
                protocolId=E_PROTOCOL_ID.JOB_COMPLETE.value,
                sender=sender,
                receiver=receiver,
                jobId=job_id,
                vehicleId=vehicle_id,
                sensorType=sensor_type,
                moduleType=module_type,
            ),
        )
        self._register(
            E_PROTOCOL_ID.ERROR_NOTI.value,
            decoder=lambda raw: ProtocolMeta.from_json(ErrorNoti, raw),
            factory=lambda sender, receiver, comment, job_id, error_type: ErrorNoti(
                protocolId=E_PROTOCOL_ID.ERROR_NOTI.value,
                sender=sender,
                receiver=receiver,
                comment=comment,
                jobId=job_id,
                errorType=error_type,
            ),
        )
        self._register(
            E_PROTOCOL_ID.MESSAGE_NOTI.value,
            decoder=lambda raw: ProtocolMeta.from_json(MessageNoti, raw),
            factory=lambda sender, receiver, comment: MessageNoti(
                protocolId=E_PROTOCOL_ID.MESSAGE_NOTI.value,
                sender=sender,
                receiver=receiver,
                comment=comment,
            ),
        )

    def _register(self, protocol_id: str, *, decoder: _DecoderFn, factory: _FactoryFn) -> None:
        if protocol_id in self._entries:
            raise KeyError(f"Protocol already registered: {protocol_id}")
        self._entries[protocol_id] = ProtocolEntry(decoder=decoder, factory=factory)

    def get_factory(self, protocol_id: str) -> _FactoryFn:
        return self._entries[protocol_id].factory

    def get_decoder(self, protocol_id: str) -> _DecoderFn:
        return self._entries[protocol_id].decoder

    def decode_body(self, json_body: str) -> abMessage:
        """raw json 의 protocolId 필드로 dispatch."""
        protocol_id = json.loads(json_body).get("protocolId")
        if protocol_id is None:
            raise ValueError("missing protocolId in message body")
        return self._entries[protocol_id].decoder(json_body)

    # --- serializer ---

    @staticmethod
    def to_json(obj: abMessage) -> str:
        return json.dumps(asdict(obj))

    @staticmethod
    def from_json(target_cls: Type[T], json_string: str) -> T:
        return target_cls(**json.loads(json_string))
