from __future__ import annotations

import ctypes
import platform


def build_cpp_library_for_camera(process_index: int) -> ctypes.CDLL | None:
    """카메라(AM20) 추출 process 만 libgstreamer.so 를 load.

    process_index % 10 < 4 조건은 카메라 추출에 필요한 process group 만 cpp library 를
    로드하던 device-balancing 코드. Windows 에선 GStreamer 미지원이므로 None 반환.
    """
    if platform.system() == "Windows":
        return None
    if process_index % 10 >= 4:
        return None

    cpp = ctypes.CDLL("./src/drivers/am20/libam20_converter.so")
    cpp.appendBuffer.argtypes = [ctypes.c_char_p]
    cpp.createPipeline()
    cpp.addElement()
    cpp.linkElements()
    cpp.addProbe()
    return cpp
