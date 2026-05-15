from dataclasses import dataclass

from protocol.base_protocol import BaseProtocol
# 추출 잡 한 건의 packet — sensor type / module type / src path / dst path 모두 포함.
@dataclass
class JobPacket(BaseProtocol):
    jobId: str = ""
    vehicleId: str = ""
    sensorType: str = ""
    moduleType: str = ""
    srcPath: str = ""
    dstPath: str = ""

    def __init__(
        self,
        sender: str,
        job_id: str,
        vehicle_id: str,
        sensor_type: str,
        module_type: str,
        src_path: str,
        dst_path: str,
    ) -> None:
        from protocol.protocol_meta import ProtocolMeta
        super().__init__(ProtocolMeta.E_PROTOCOL_ID.JOB_REQUEST, sender)
        self.jobId = job_id
        self.vehicleId = vehicle_id
        self.sensorType = sensor_type
        self.moduleType = module_type
        self.srcPath = src_path
        self.dstPath = dst_path

    def get_job_id(self) -> str:
        return self.jobId

    def get_vehicle_id(self) -> str:
        return self.vehicleId

    def get_sensor_type(self) -> str:
        return self.sensorType

    def get_module_type(self) -> str:
        return self.moduleType

    def get_src_path(self) -> str:
        return self.srcPath

    def get_dst_path(self) -> str:
        return self.dstPath
