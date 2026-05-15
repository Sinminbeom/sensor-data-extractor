from extractor.extract_context import ExtractContext
from extractor.extract import IExtract
# IMU 추출은 GNSS 추출과 알고리즘이 동일 (같은 cpp/messages_public.json 사용) — GnssExtract 에 위임.
class ImuExtract(IExtract):
    """IMU pcap → ASCII 결과 파일 변환."""

    @staticmethod
    def extract(ctx: ExtractContext) -> None:
        from extractor.sensors.gnss_extract import GnssExtract
        GnssExtract.extract(ctx)
