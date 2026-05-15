from python_library.define.enum import IENUM
# PCAP file/payload 처리 시 사용되는 link type / protocol 상수. 외부 의존 없애기 위해 로컬화.
# `IPCap` 컨테이너 클래스 제거 후 module-level enum 두 개로 노출.
class E_LINK_TYPE(IENUM):
    ETHERNET = 1
    LINUX_SLL = 113
    LINUX_SLL_V2 = 276

class E_PROTOCOL(IENUM):
    TCP = 6
    UDP = 17
