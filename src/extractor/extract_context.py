from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ExtractContext:
    """단일 추출 작업의 입력/주변 상태를 묶는 frozen-like dataclass.

    ctypes / GStreamer 핸들은 cpp_library 필드로 별도 주입 — 데이터 모듈을
    가볍게 유지하기 위해 헬퍼는 extractor.gstreamer.cpp_library 로 분리.
    """

    name: str
    source_storage: Any
    destination_storage: Any
    tmp_pcap_saved_path: str
    tmp_result_saved_path: str
    protocol: Any
    gstreamer_state: Any
    vehicles: Any
    cpp_library: Any | None = None
