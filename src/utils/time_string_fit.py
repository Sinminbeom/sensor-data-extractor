from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from python_library.define.enum import IENUM
# 외부 dependency를 없애기 위해 동일 인터페이스로 로컬화. PCAP message buffer가 앞/뒤 file
# timestamp 계산에 사용.
class E_CALENDAR_TYPE(IENUM):
    YEAR = "YEAR"
    MONTH = "MONTH"
    DAY = "DAY"
    HOUR = "HOUR"
    MIN = "MIN"
    SEC = "SEC"

# 시간 문자열 포맷: "YYYYMMDDHHMMSS" (14자)
_TIME_FORMAT = "%Y%m%d%H%M%S"

class TimeStringInterval:

    def __init__(self, calendar_type: str, value: int) -> None:
        self.calendar_type = calendar_type
        self.value = value

class TimeStringFit:

    def __init__(self) -> None:
        self._dt: datetime | None = None

    def set(self, time_string: str) -> "TimeStringFit":
        self._dt = datetime.strptime(time_string, _TIME_FORMAT)
        return self

    def get(self) -> str:
        return self._dt.strftime(_TIME_FORMAT)

    def next_element(self, calendar_type: str, value: int) -> "TimeStringFit":
        delta_map = {
            E_CALENDAR_TYPE.SEC: timedelta(seconds=value),
            E_CALENDAR_TYPE.MIN: timedelta(minutes=value),
            E_CALENDAR_TYPE.HOUR: timedelta(hours=value),
            E_CALENDAR_TYPE.DAY: timedelta(days=value),
        }
        if calendar_type in delta_map:
            self._dt = self._dt + delta_map[calendar_type]
        elif calendar_type == E_CALENDAR_TYPE.MONTH:
            self._dt = self._dt + timedelta(days=30 * value)
        elif calendar_type == E_CALENDAR_TYPE.YEAR:
            self._dt = self._dt + timedelta(days=365 * value)
        return self

    def coroutine(
        self,
        from_time: str,
        to_time: str,
        interval: TimeStringInterval,
        on_tick: Callable[["TimeStringFit"], None],
        compare: str,
    ) -> None:
        # compare: '<' or '>' — 비교 연산자 (interval 방향에 따라 다름)
        cursor = TimeStringFit().set(from_time)
        target_dt = datetime.strptime(to_time, _TIME_FORMAT)

        if compare == "<":
            condition = lambda c: c < target_dt
        else:
            condition = lambda c: c > target_dt

        while condition(cursor._dt):
            on_tick(cursor)
            cursor.next_element(interval.calendar_type, interval.value)
            new_dt = cursor._dt
            cursor = TimeStringFit()
            cursor._dt = new_dt
