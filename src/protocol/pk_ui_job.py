from dataclasses import dataclass

from protocol.base_protocol import BaseProtocol
# UI → Web service 잡 요청 packet.
@dataclass
class PkUiJob(BaseProtocol):
    date: str = ""
    vehicleId: str = ""

    def __init__(
        self,
        protocol_id: str = "",
        sender: str = "",
        date: str = "",
        vehicle_id: str = "",
    ) -> None:
        super().__init__(protocol_id, sender)
        self.date = date
        self.vehicleId = vehicle_id

    def get_date(self) -> str:
        return self.date

    def get_vehicle_id(self) -> str:
        return self.vehicleId
