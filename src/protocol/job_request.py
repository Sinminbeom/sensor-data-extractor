from dataclasses import dataclass

from protocol.message import abMessage
# 추출 잡 한 건의 packet — sensor type / module type / src path / dst path 모두 포함.
@dataclass(kw_only=True)
class JobRequest(abMessage):
    jobId: str
    vehicleId: str
    sensorType: str
    moduleType: str
    srcPath: str
    dstPath: str
