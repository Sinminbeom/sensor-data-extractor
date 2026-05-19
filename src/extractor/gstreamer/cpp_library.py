from __future__ import annotations

import platform
from typing import Any


def build_cpp_library_for_camera(process_index: int) -> Any | None:
    """카메라(AM20) 추출 worker process 만 native GStreamer pybind11 모듈을 로드.

    GPU 변형 (am20_converter) 을 우선 시도하고, DeepStream/NVIDIA 가 없는 환경에서
    실패하면 CPU 변형 (am20_converter_cpu) 으로 fallback. Windows 미지원.

    process_index % 10 < 4 조건은 device-balancing — 4 개 process 만 cpp 모듈 로드.
    """
    if platform.system() == "Windows":
        return None
    if process_index % 10 >= 4:
        return None

    try:
        from drivers.am20 import am20_converter as _mod
    except ImportError:
        from drivers.am20 import am20_converter_cpu as _mod  # type: ignore

    converter = _mod.AM20Converter({})
    converter.addElement()
    converter.linkElements()
    converter.addProbe()
    return converter
