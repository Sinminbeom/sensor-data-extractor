import json
from dataclasses import asdict, dataclass
# 모든 프로토콜 packet의 base — protocolId + sender만 갖는 minimal 구조.
@dataclass
class BaseProtocol:
    protocolId: str = ""
    sender: str = ""

    def get_protocol_id(self) -> str:
        return self.protocolId

    def get_sender(self) -> str:
        return self.sender

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
