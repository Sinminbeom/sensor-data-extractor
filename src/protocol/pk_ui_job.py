from dataclasses import dataclass

from protocol.message import abMessage
# UI → Web service 잡 요청 packet.
@dataclass(kw_only=True)
class PkUiJob(abMessage):
    date: str
    vehicleId: str
