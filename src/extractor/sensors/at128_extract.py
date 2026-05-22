import os
import re

from python_library.logger.app_logger import AppLogger

from extractor.extract_context import ExtractContext
from extractor.extract import IExtract
from pcap.filter.at128_filter import At128Filter
from pcap.message_buffer import PcapMessageBuffer
from pcap.sensor.at128_payload import At128PayloadData
from pcap.sll2_to_ethernet import At128EthernetConvert
from utils.shell_util import ShellUtil
# AT128 (rooftop Hesai LiDAR) PCAP → PCD 변환.
# 처리 흐름:
#   1) source storage에서 대상 pcap + 앞/뒤 1초 pcap 동시 로드 (총 3초 분량)
#   2) azimuth 변화 지점 기준으로 시작/끝 packet 자르기
#   3) SLL2 → Ethernet 변환 후 임시 pcap 저장
#   4) 차량별 driver(C++ at128_converter)에 던져 PCD 변환
#   5) 결과 tar로 묶어 destination storage 업로드 + 임시 파일 정리
class At128Extract(IExtract):
    FILE_NAME_PATTERN = re.compile(r"(.+)_([0-9]+)\.pcap")
    PCD_RESULT_PATTERN = re.compile(r"(\S+\.bin)")
    _DRIVER_BY_SENSOR = {
        "at128_roof_front": "eth_e_a",
        "at128_roof_right": "eth_e_b",
        "at128_roof_rear": "eth_e_c",
        "at128_roof_left": "eth_e_d",
        "rsbp_bump_front": "eth_e_i",
        "rsbp_bump_right": "eth_e_j",
        "rsbp_bump_rear": "eth_e_k",
        "rsbp_bump_left": "eth_e_l",
    }

    @staticmethod
    def extract(ctx: ExtractContext) -> None:
        dst_storage = ctx.destination_storage
        vehicles = ctx.vehicles

        try:
            src_path = ctx.protocol.srcPath
            AppLogger.instance().info(f"Read At128 File From Storage -> {src_path}")

            message_buffer = At128Extract._read_file(ctx)

            start_pick, end_pick = message_buffer.get_buffer().get_original_file_indexes()

            if message_buffer.get_before_file_count() == 1:
                front_idx = At128Extract._find_right_packet_index(
                    message_buffer, 0, start_pick, At128Extract._azimuth_changed
                )
                start_pick = front_idx + 1

            if message_buffer.get_after_file_count() == 1:
                if At128Extract._is_connected_end_azimuth(message_buffer, end_pick):
                    final_idx = At128Extract._find_right_packet_index(
                        message_buffer, 0, end_pick, At128Extract._azimuth_changed
                    )
                    end_pick = final_idx

            tmp_save_path = ctx.tmp_pcap_saved_path + At128Extract._vehicle_id(ctx) + "/"
            os.makedirs(tmp_save_path, exist_ok=True)
            tmp_result_path = ctx.tmp_result_saved_path + At128Extract._vehicle_id(ctx) + "/"
            os.makedirs(tmp_result_path, exist_ok=True)

            normalized_path = At128Extract._save_tmp_pcap(
                tmp_save_path, src_path, message_buffer, start_pick, end_pick
            )
            AppLogger.instance().info(f"save AT128 Normalized Tmp Pcap File : {normalized_path}")

            match = At128Extract.FILE_NAME_PATTERN.match(os.path.basename(src_path))
            sensor_name, date = match.groups()

            # SLL2 capture → 표준 Ethernet pcap 변환
            At128EthernetConvert().convert(normalized_path, normalized_path)

            params = {
                "srcPath": normalized_path,
                "lidarName": sensor_name,
                "timestamp": date,
                "dstPath": tmp_result_path,
            }

            driver_key = At128Extract._DRIVER_BY_SENSOR[sensor_name]
            vehicle_id = ctx.protocol.vehicleId or "E100_4"
            drivers = vehicles.get(vehicle_id)
            driver = drivers.get(driver_key)
            driver.on_start(params)
            driver.on_stop()
            extracted_files = driver.get_dst_path_list()

            At128Extract._delete_file(normalized_path)

            At128Extract._upload(
                tmp_result_path, ctx, src_path, extracted_files, dst_storage,
                ctx.protocol.dstPath
            )
            At128Extract._delete_tmp_files(extracted_files)

        except Exception as e:
            AppLogger.instance().exception(e)
            raise

    # --- helpers ---

    @staticmethod
    def _read_file(ctx: ExtractContext) -> PcapMessageBuffer:
        message_buffer = PcapMessageBuffer(
            ctx.source_storage, ctx.protocol.srcPath, At128Filter(At128PayloadData)
        )
        message_buffer.read_previous_file()
        message_buffer.read_next_file()
        return message_buffer

    @staticmethod
    def _find_right_packet_index(message_buffer, start, end, predicate):
        return message_buffer.get_buffer().compare_range_adjacency_with_func(
            start, end + 1,
            lambda target, compare: predicate(target, compare),
            iter_reverse=True,
        )

    @staticmethod
    def _azimuth_changed(target, compare) -> bool:
        t = target.get_payload_pretty(At128PayloadData).get_azimuth()
        c = compare.get_payload_pretty(At128PayloadData).get_azimuth()
        if t is None or c is None:
            return False
        return abs(t - c) > 300

    @staticmethod
    def _is_connected_end_azimuth(message_buffer, end) -> bool:
        message_buffer.seek(end)
        end_elem = message_buffer.get_buffer().get_current_element()
        end_az = end_elem.get_payload_pretty(At128PayloadData).get_azimuth()

        message_buffer.seek(end + 1)
        next_elem = message_buffer.get_buffer().get_current_element()
        next_az = next_elem.get_payload_pretty(At128PayloadData).get_azimuth()

        if end_az is None or next_az is None:
            return False
        return abs(end_az - next_az) < 300

    @staticmethod
    def _save_tmp_pcap(tmp_path: str, src_path: str, message_buffer,
                       start: int, end: int) -> str:
        message_buffer.get_buffer().start_marking(start)
        if end < 0:
            end = message_buffer.get_buffer().get_end_cursor()
        message_buffer.get_buffer().end_marking(end)
        picked = message_buffer.get_buffer().pick()
        normalized = tmp_path + os.path.basename(src_path)
        picked.save(normalized)
        return normalized

    @staticmethod
    def _upload(tmp_result_path: str, ctx: ExtractContext, src_file: str,
                upload_files, dst_storage, dst_path: str) -> None:
        # python-library IStorage.upload(src, dst)는 dst가 파일 절대경로이므로 dst에 zip filename을 명시적으로 결합.
        if not upload_files:
            return

        original = os.path.basename(src_file).split(".")[0]
        zip_path = tmp_result_path + original + ".tar"

        ShellUtil(f"rm -rf {zip_path}", True).run()
        cmd = f"tar -cvf {zip_path} {tmp_result_path}{original}*"
        _, stderr = ShellUtil(cmd, True).run()
        if stderr and "tar: Removing leading `/'" not in stderr:
            return

        target = f"{dst_path}/{At128Extract._vehicle_id(ctx)}/{os.path.basename(zip_path)}"
        AppLogger.instance().info(f"Upload Result file : {zip_path} => {target}")
        dst_storage.upload(zip_path, target)
        At128Extract._delete_file(zip_path)

    @staticmethod
    def _vehicle_id(ctx: ExtractContext) -> str:
        return os.path.dirname(ctx.protocol.srcPath).split("/")[2]

    @staticmethod
    def _delete_tmp_files(files) -> None:
        for f in files:
            At128Extract._delete_file(f)

    @staticmethod
    def _delete_file(path: str) -> None:
        if os.path.exists(path):
            AppLogger.instance().info(f"delete {path}")
            os.remove(path)
