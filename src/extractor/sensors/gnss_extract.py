import os

from python_library.define.enum import IENUM
from python_library.logger.app_logger import AppLogger

from drivers.imu.text_conv import ImuTextConv
from extractor.extract_context import ExtractContext
from extractor.extract import IExtract
from pcap.message_buffer import PcapMessageBuffer
# GNSS 메시지를 정형화하는 C++ extractor에 넘기는 메타 (json db + 인코딩 형식).
class E_GNSS_CPP_EXTRACTOR(IENUM):
    FORMAT = "ASCII"
    DATABASE = "./src/drivers/imu/messages_public.json"
# 클래스명 cGnssExtract → GnssExtract 그대로, 메서드는 snake_case.
class GnssExtract(IExtract):
    """GNSS pcap → ASCII 결과 파일 변환 + 업로드."""

    @staticmethod
    def extract(ctx: ExtractContext) -> None:
        dst_storage = ctx.destination_storage

        try:
            src_path = ctx.protocol.srcPath
            AppLogger.instance().info(f"Read GNSS File From Storage : {src_path}")

            message_buffer = GnssExtract._read_file(ctx)

            # 다음 1초 pcap에서 b'\xaaD' sync 패턴을 KMP로 찾아 3개 누적될 때까지 진행
            start_pick, end_pick = message_buffer.get_buffer().get_original_file_indexes()
            cnt = 0

            if message_buffer.get_after_file_count() == 1:
                buf = message_buffer.get_buffer()
                next_start, next_end = buf.indexRecord.search_after_file_indexes(1)
                for elem_idx in range(next_start, next_end):
                    cnt += GnssExtract._verify_func(buf.pcapElements[elem_idx])
                    if cnt > 3:
                        end_pick = elem_idx
                        break

            vehicle_id = GnssExtract._vehicle_id(ctx)
            tmp_save_path = ctx.tmp_pcap_saved_path + vehicle_id + "/"
            os.makedirs(tmp_save_path, exist_ok=True)

            tmp_result_path = ctx.tmp_result_saved_path + vehicle_id + "/"
            os.makedirs(tmp_result_path, exist_ok=True)

            normalized = GnssExtract._save_tmp_pcap(
                tmp_save_path, ctx, message_buffer, start_pick, end_pick
            )

            params = {
                "sJsonDB": E_GNSS_CPP_EXTRACTOR.DATABASE,
                "sEncodeFormat": E_GNSS_CPP_EXTRACTOR.FORMAT,
                "sInFilePath": normalized,
                "sPrefixFilePath": tmp_result_path,
            }

            text_conv = ImuTextConv(params)
            text_conv.start()
            text_conv.join()

            pcap_filename = GnssExtract._filename_from_job_id(src_path)
            extracted = f"{tmp_result_path}{pcap_filename}.{E_GNSS_CPP_EXTRACTOR.FORMAT}"

            GnssExtract._filter_result(extracted, cnt)
            target = f"{ctx.protocol.dstPath}/{vehicle_id}/{os.path.basename(extracted)}"
            dst_storage.upload(extracted, target)
            AppLogger.instance().info(f"Upload Result file : {extracted} => {target}")

            GnssExtract._delete_tmp_files(normalized, extracted)

        except Exception as e:
            AppLogger.instance().exception(e)
            raise

    # --- helpers ---

    @staticmethod
    def _read_file(ctx: ExtractContext) -> PcapMessageBuffer:
        message_buffer = PcapMessageBuffer(
            ctx.source_storage, ctx.protocol.srcPath
        )
        message_buffer.read_next_file()
        return message_buffer

    @staticmethod
    def _save_tmp_pcap(tmp_path: str, ctx: ExtractContext, message_buffer,
                       start: int, end: int) -> str:
        message_buffer.get_buffer().start_marking(start)
        if end < 0:
            end = message_buffer.get_buffer().get_end_cursor()
        message_buffer.get_buffer().end_marking(end)
        picked = message_buffer.get_buffer().pick()

        normalized = tmp_path + GnssExtract._filename_from_job_id(ctx.protocol.srcPath)
        AppLogger.instance().info(f"save Gnss Normalized Tmp Pcap File : {normalized}")
        picked.save(normalized)
        return normalized

    @staticmethod
    def _verify_func(element) -> int:
        payload = element.get_payload().tobytes()
        return len(GnssExtract._kmp_search(payload, b"\xaaD"))

    @staticmethod
    def _filter_result(file_path: str, remove_row_cnt: int) -> None:
        with open(file_path, "r") as f:
            lines = f.readlines()
        with open(file_path, "w") as f:
            f.writelines(lines[:-remove_row_cnt])

    @staticmethod
    def _kmp_search(s: bytes, pattern: bytes) -> list[int]:
        def compute_prefix(p: bytes) -> list[int]:
            prefix_len = 0
            lps = [0] * len(p)
            i = 1
            while i < len(p):
                if p[i] == p[prefix_len]:
                    prefix_len += 1
                    lps[i] = prefix_len
                    i += 1
                else:
                    if prefix_len != 0:
                        prefix_len = lps[prefix_len - 1]
                    else:
                        lps[i] = 0
                        i += 1
            return lps

        lps = compute_prefix(pattern)
        i = j = 0
        result: list[int] = []
        while i < len(s):
            if pattern[j] == s[i]:
                i += 1
                j += 1
            if j == len(pattern):
                result.append(i - j)
                j = lps[j - 1]
            elif i < len(s) and pattern[j] != s[i]:
                if j != 0:
                    j = lps[j - 1]
                else:
                    i += 1
        return result

    @staticmethod
    def _filename_from_job_id(src_path: str) -> str:
        job_id = os.path.basename(src_path)
        return "_".join(job_id.split("_")[-2:])

    @staticmethod
    def _delete_tmp_files(tmp_pcap: str, tmp_result: str) -> None:
        GnssExtract._delete_file(tmp_pcap)
        GnssExtract._delete_file(tmp_result)

    @staticmethod
    def _delete_file(path: str) -> None:
        if os.path.exists(path):
            os.remove(path)

    @staticmethod
    def _vehicle_id(ctx: ExtractContext) -> str:
        return os.path.dirname(ctx.protocol.srcPath).split("/")[2]
