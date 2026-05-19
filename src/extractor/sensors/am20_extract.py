import ctypes
import glob
import os
import platform
import tarfile
import time
from decimal import Decimal
from typing import Tuple

from python_library.logger.app_logger import AppLogger
from python_library.storage.s3.s3_storage_factory import S3StorageFactory
from python_library.storage.s3.s3_storage_info_factory import S3StorageInfoFactory

from extractor.extract_context import ExtractContext
from extractor.extract import IExtract
from pcap.message_buffer import PcapMessageBuffer

# GStreamer는 Linux/CUDA(deepstream) 환경에서만 동작
if platform.system() != "Windows":
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst, GLib  # noqa: F401
    except Exception:
        pass
# AM20 (HD camera, 10 방향) 영상 PCAP → 키프레임 JPG 추출.
# 처리 흐름:
#   1) 대상 pcap + 앞/뒤 1초 pcap 동시 로드 후 timestamp 순으로 sort
#   2) MPEG2-TS 패킷 안에서 PAT(Program Association Table) 패킷과 IDR(키프레임) 위치를 KMP 검색으로 탐지
#   3) 마지막 PAT부터 다음 IDR까지를 잘라 GStreamer pipeline에 push
#   4) GStreamer(rtpmp2tdepay → tsdemux → h265parse → nvv4l2decoder → nvvideoconvert → pngenc → multifilesink)
#   5) GStreamer callback에서 tar로 묶어 destination_storage 업로드
class Am20Extract(IExtract):
    @staticmethod
    def extract(ctx: ExtractContext) -> None:
        if platform.system() == "Windows":
            return

        start = time.time()

        dst_storage = ctx.destination_storage
        src_path = ctx.protocol.get_src_path()
        original_filename = Am20Extract._original_filename(ctx)
        vehicle_id = Am20Extract._vehicle_id(ctx)
        cpp_library = ctx.cpp_library
        gstreamer_state = ctx.gstreamer_state

        base_timestamp = 0
        seq_num_before = 0
        payload_len_before = 0
        loop_cnt = 0
        callback_func_type = ctypes.CFUNCTYPE(
            None,
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_char_p),
        )
        callback_func = callback_func_type(Am20Extract._custom_callback)
        cpp_library.registerPythonCallback(callback_func)

        try:
            tmp_save_path = f"{ctx.tmp_pcap_saved_path}{vehicle_id}/"
            tmp_result_path = f"{ctx.tmp_result_saved_path}{vehicle_id}/"
            dst_path = f"{ctx.protocol.get_dst_path()}/{vehicle_id}"

            AppLogger.instance().info(f"Read Camera File From Storage : {src_path}")
            message_buffer = Am20Extract._read_file(dst_storage, src_path)

            # 앞/뒤 file이 둘 다 있어야 정상 추출 가능 — 없으면 skip
            if message_buffer.get_after_file_count() != 1:
                return
            if message_buffer.get_before_file_count() != 1:
                return

            message_buffer.sort()
            message_buffer.seek(0)

            cpp_library.setProperty(
                tmp_result_path.encode("utf-8"),
                original_filename.encode("utf-8"),
                dst_path.encode("utf-8"),
                str(start).encode("utf-8"),
            )
            if message_buffer.get_before_file_count() == 1:
                buf = message_buffer.get_buffer()
                origin_idr_idx = buf.verify_second_with_func(0, Am20Extract._idr_search, True)
                last_pat_idx, last_pat_bytes_idx = buf.verify_range_with_func2(
                    0, origin_idr_idx, Am20Extract._verify_func, True
                )
                next_idr_idx, next_idr_bytes_idx = buf.verify_second_with_func2(
                    1, Am20Extract._idr_search2
                )

            # 위에서 못 찾은 케이스는 모두 skip
            if origin_idr_idx < 0:
                AppLogger.instance().exception(f"originIDRIndex Not Found : {src_path}")
                return
            if last_pat_idx < 0:
                AppLogger.instance().exception(f"lastPATIndex Not Found : {src_path}")
                return
            if next_idr_idx < 0:
                AppLogger.instance().exception(f"nextIDRIndex Not Found : {src_path}")
                return
            if last_pat_bytes_idx < 0:
                AppLogger.instance().exception(f"lastPATBytesIdx Not Found : {src_path}")
                return
            if next_idr_bytes_idx < 0:
                AppLogger.instance().exception(f"nextIDRBytesIdx Not Found : {src_path}")
                return

            message_buffer.get_buffer().start_marking(last_pat_idx)
            message_buffer.get_buffer().end_marking(next_idr_idx)
            picked = message_buffer.get_buffer().pick()

            cpp_library.start()
            cpp_library.setGstStatePlay()

            # picked buffer를 순회하며 sequence number 검증 + GStreamer로 payload 푸시
            while True:
                current = picked.get_current_element()
                if current is None:
                    break

                loop_cnt += 1
                seq_num_expected = seq_num_before + payload_len_before

                if loop_cnt == 1:
                    pass
                else:
                    if seq_num_expected != current.get_pcap_body().get_seq_num():
                        # sequence gap이면 buffer는 건너뛰고 base만 갱신
                        seq_num_before = current.get_pcap_body().get_seq_num()
                        payload_len_before = len(current.get_payload())
                        picked.next_element()
                        continue

                if base_timestamp == 0:
                    base_timestamp = current.get_pcap_packet_header().get_timestamp()

                timestamp = current.get_pcap_packet_header().get_timestamp()
                # gstreamer pipeline에 PTS로 넘기기 위한 시간 계산
                nanosec = (
                    Decimal(timestamp - base_timestamp) * Decimal(1_000_000_000)
                ) + Decimal(gstreamer_state.last_nano_sec)

                decimal_bytes = str(nanosec).encode("utf-8")

                if picked.get_current_cursor() == picked.get_end_cursor():
                    # 마지막 packet: 다음 IDR 위치까지만 자른다
                    payload = current.get_payload()[:next_idr_bytes_idx].tobytes()
                    cpp_library.appendBuffer(payload, decimal_bytes, len(payload))
                elif picked.get_current_cursor() == picked.get_start_cursor():
                    # 첫 packet: 마지막 PAT 위치 이후만 사용
                    payload = current.get_payload()[last_pat_bytes_idx:].tobytes()
                    cpp_library.appendBuffer(payload, decimal_bytes, len(payload))
                else:
                    payload = current.get_payload().tobytes()
                    cpp_library.appendBuffer(payload, decimal_bytes, len(payload))

                if picked.get_current_cursor() == picked.get_end_cursor():
                    gstreamer_state.last_nano_sec = gstreamer_state.last_nano_sec + nanosec + 61988

                seq_num_before = current.get_pcap_body().get_seq_num()
                payload_len_before = len(current.get_payload())

                if picked.next_element() is None:
                    break

            os.makedirs(tmp_save_path, exist_ok=True)
            os.makedirs(tmp_result_path, exist_ok=True)

            cpp_library.addIdle()
            cpp_library.join()

        except Exception as e:
            AppLogger.instance().exception(e)
            raise

    # --- helpers ---

    @staticmethod
    def _read_file(storage, src_path: str, filter_obj=None) -> PcapMessageBuffer:
        message_buffer = PcapMessageBuffer(storage, src_path, filter_obj)
        message_buffer.read_previous_file_until(1)
        message_buffer.read_next_file_until(1)
        return message_buffer

    @staticmethod
    def _verify_func(element) -> Tuple[bool, int]:
        pid_mask = 0x001FFF00
        continuity_counter_mask = 0x0F
        start_seq = b"G@"
        payload = element.get_payload().tobytes()

        for idx in Am20Extract._kmp_search(payload, start_seq):
            if idx + 3 > len(payload) - 1:
                continue
            if payload[idx + 3] & continuity_counter_mask > 15:
                continue
            # Adaptation Field Control: 0b11 (Adaptation Field + Payload)
            if payload[idx + 3] >> 4 != 3:
                continue
            header = int.from_bytes(payload[idx : idx + 4], byteorder="big")
            if header & pid_mask == 0:
                return True, idx
        return False, -1

    @staticmethod
    def _idr_search(element) -> bool:
        nal_start = b"\x00\x00\x00\x01"
        payload = element.get_payload().tobytes()
        for idx in Am20Extract._kmp_search(payload, nal_start):
            if idx + len(nal_start) > len(payload) - 1:
                continue
            nal_unit_type = element.get_payload()[idx + len(nal_start)] & 0x1F
            if nal_unit_type == 5:
                return True
        return False

    @staticmethod
    def _idr_search2(element) -> Tuple[bool, int]:
        nal_start = b"\x00\x00\x00\x01"
        payload = element.get_payload().tobytes()
        for idx in Am20Extract._kmp_search(payload, nal_start):
            if idx + len(nal_start) > len(payload) - 1:
                continue
            nal_unit_type = element.get_payload()[idx + len(nal_start)] & 0x1F
            if nal_unit_type == 5:
                return True, idx
        return False, -1

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
    def _vehicle_id(ctx: ExtractContext) -> str:
        return os.path.dirname(ctx.protocol.get_src_path()).split("/")[2]

    @staticmethod
    def _original_filename(ctx: ExtractContext) -> str:
        return os.path.basename(ctx.protocol.get_src_path()).split(".")[0]

    @staticmethod
    def _custom_callback(tmp_result_p, original_p, dst_p, start_p) -> None:
        # 결과를 tar로 묶어 storage 업로드 + 임시 jpg들 정리.
        tmp_result = tmp_result_p[0].decode("utf-8")
        original = original_p[0].decode("utf-8")
        dst_path = dst_p[0].decode("utf-8")
        start_time = start_p[0].decode("utf-8")
        storage = S3StorageFactory(S3StorageInfoFactory()).create_storage()
        storage.connect()
        Am20Extract._upload(storage, tmp_result, original, dst_path)
        Am20Extract._delete_tmp_files(tmp_result, original)
        storage.disconnect()

        end = time.time()
        AppLogger.instance().info(f"Camera extract Time : {end - float(start_time)}")

    @staticmethod
    def _upload(dst_storage, tmp_result_path: str, original: str, dst_path: str) -> None:
        tar_path = f"{tmp_result_path}{original}.tar"
        if os.path.exists(tar_path):
            os.remove(tar_path)

        with tarfile.open(tar_path, "w") as tar:
            for f in glob.glob(f"{tmp_result_path}{original}*.jpg"):
                tar.add(f)

        target = f"{dst_path}/{os.path.basename(tar_path)}"
        AppLogger.instance().info(f"Upload Result file : {tar_path} => {target}")
        dst_storage.upload(tar_path, target)
        Am20Extract._delete_file(tar_path)

    @staticmethod
    def _delete_tmp_files(tmp_result_path: str, original: str) -> None:
        for f in glob.glob(f"{tmp_result_path}{original}*.jpg"):
            os.remove(f)

    @staticmethod
    def _delete_file(path: str) -> None:
        if os.path.exists(path):
            os.remove(path)
