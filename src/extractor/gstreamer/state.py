# 카메라(AM20) 추출 시 multi-process가 공유하는 nanosec 누적치 보관용 simple state.
# 클래스명 cGstreamerState → GstreamerState. PascalCase 호환 메서드는 제거 (사용처에서 snake_case로 호출).
class GstreamerState:
    def __init__(self) -> None:
        self.last_nano_sec: int = 0
