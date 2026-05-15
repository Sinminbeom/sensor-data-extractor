from python_library.define.enum import IENUM
# 추출기 dispatch 키 — sensor_category 의 E_SENSOR_TYPE 과 다른 layer.
# 같은 LIDAR 라도 AT128 / RSBP 는 별도 추출 파이프라인을 가지므로 모듈 단위 식별이 필요.
class E_MODULE_TYPE(IENUM):
    AT128 = "AT128"
    RSBP = "RSBP"
    AM20 = "AM20"
    IMU = "IMU"
    GNSS = "GNSS"
