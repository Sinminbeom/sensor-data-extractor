from dataclasses import dataclass

from protocol.base_protocol import BaseProtocol
# 잡 완료 packet — ExtractorWorker가 처리 성공 시 발행.
@dataclass
class JobComplete(BaseProtocol):
    jobId: str = ""
    vehicleId: str = ""
    sensorType: str = ""
    moduleType: str = ""

    def __init__(
        self,
        sender: str,
        job_id: str,
        vehicle_id: str,
        sensor_type: str,
        module_type: str,
    ) -> None:
        from protocol.protocol_meta import ProtocolMeta
        super().__init__(ProtocolMeta.E_PROTOCOL_ID.JOB_COMPLETE, sender)
        self.jobId = job_id
        self.vehicleId = vehicle_id
        self.sensorType = sensor_type
        self.moduleType = module_type

    def get_job_id(self) -> str:
        return self.jobId

    def get_vehicle_id(self) -> str:
        return self.vehicleId

    def get_sensor_type(self) -> str:
        return self.sensorType

    def get_module_type(self) -> str:
        return self.moduleType
