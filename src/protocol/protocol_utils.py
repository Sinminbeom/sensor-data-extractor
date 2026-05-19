from datetime import datetime

from python_library.singleton.singleton import Singleton
# Jenkins build name 에 들어가는 sequence id ("YYYYMMDDHHMMSS_NNNNNNNN") 생성기.
class ProtocolUtils(Singleton):
    def __init__(self) -> None:
        self._sequence_id: dict[str, int] = {}

    def initialize(self) -> "ProtocolUtils":
        self._sequence_id = {}
        return self

    def get_sequence_id_now(self) -> str:
        # 1 초 단위 키에서 카운터 증가 후 zero-padded suffix
        field_key = datetime.now().strftime("%Y%m%d%H%M%S")
        if field_key in self._sequence_id:
            self._sequence_id[field_key] += 1
        else:
            self._sequence_id[field_key] = 0
        seq = self._sequence_id[field_key]
        return f"{field_key}_{seq:08}"
