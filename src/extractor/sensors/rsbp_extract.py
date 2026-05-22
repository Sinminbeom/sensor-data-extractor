import os
import re
from typing import Tuple

from python_library.define.enum import IENUM
from python_library.logger.app_logger import AppLogger

from extractor.extract_context import ExtractContext
from extractor.extract import IExtract
from pcap.filter.bpearl_filter import BpearlFilter
from pcap.message_buffer import PcapMessageBuffer
from pcap.sensor.bpearl_payload import BpearlPayloadData
from pcap.sll2_to_ethernet import RsbpEthernetConvert
from utils.shell_util import ShellUtil


class RsbpPortMeta(IENUM):
    RSBP_MAP: dict[str, str] = {
        "6699": "7788",
        "6700": "7789",
        "6701": "7790",
        "6702": "7791",
    }

    @staticmethod
    def find_difop_port(msop_port: str) -> str:
        return RsbpPortMeta.RSBP_MAP[str(msop_port)]


class RsbpExtract(IExtract):
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
            AppLogger.instance().info(f"Read Rsbp File From Storage -> {src_path}")

            message_buffer = RsbpExtract._read_file(ctx)
            msop_port, difop_port = RsbpExtract._find_port(message_buffer)

            start_pick, end_pick = message_buffer.get_buffer().get_original_file_indexes()

            if message_buffer.get_before_file_count() == 1:
                front_idx = RsbpExtract._find_right_packet_index(
                    message_buffer, 0, start_pick, RsbpExtract._azimuth_changed
                )
                start_pick = front_idx + 1

            if message_buffer.get_after_file_count() == 1:
                if RsbpExtract._is_connected_end_azimuth(message_buffer, end_pick):
                    final_idx = RsbpExtract._find_right_packet_index(
                        message_buffer, 0, end_pick, RsbpExtract._azimuth_changed
                    )
                    end_pick = final_idx

            tmp_result_path = ctx.tmp_result_saved_path + RsbpExtract._vehicle_id(ctx) + "/"
            os.makedirs(tmp_result_path, exist_ok=True)

            normalized_path = RsbpExtract._save_tmp_pcap(
                tmp_result_path, src_path, message_buffer, start_pick, end_pick
            )
            AppLogger.instance().info(f"save Rsbp Normalized Tmp Pcap File : {normalized_path}")

            match = RsbpExtract.FILE_NAME_PATTERN.match(os.path.basename(src_path))
            sensor_name, date = match.groups()

            RsbpEthernetConvert().convert(normalized_path, normalized_path)

            params = {
                "srcPath": normalized_path,
                "lidarName": sensor_name,
                "timestamp": date,
                "dstPath": tmp_result_path,
                "msopPort": msop_port,
                "difopPort": int(difop_port),
            }

            driver_key = RsbpExtract._DRIVER_BY_SENSOR[sensor_name]
            vehicle_id = ctx.protocol.vehicleId or "E100_4"
            drivers = vehicles.get(vehicle_id)
            driver = drivers.get(driver_key)
            driver.on_start(params)
            driver.on_stop()
            extracted_files = driver.get_dst_path_list()

            RsbpExtract._delete_file(normalized_path)

            RsbpExtract._upload(
                tmp_result_path, ctx, src_path, extracted_files, dst_storage,
                ctx.protocol.dstPath
            )
            RsbpExtract._delete_tmp_files(extracted_files)

        except Exception as e:
            AppLogger.instance().exception(e)
            raise

    # --- helpers ---

    @staticmethod
    def _read_file(ctx: ExtractContext) -> PcapMessageBuffer:
        message_buffer = PcapMessageBuffer(
            ctx.source_storage, ctx.protocol.srcPath,
            BpearlFilter(BpearlPayloadData),
        )
        message_buffer.read_previous_file()
        message_buffer.read_next_file()
        return message_buffer

    @staticmethod
    def _find_port(message_buffer) -> Tuple[int, int]:
        while True:
            element = message_buffer.get_buffer().get_current_element()
            payload = element.get_payload_pretty(BpearlPayloadData)
            if payload.get_packet_name() == BpearlPayloadData.MSOP:
                break
            message_buffer.next_element()
        body = message_buffer.get_buffer().get_current_element().get_pcap_body()
        msop = body.source_port
        difop = RsbpPortMeta.find_difop_port(msop)
        message_buffer.seek(0)
        return msop, int(difop)

    @staticmethod
    def _find_right_packet_index(message_buffer, start, end, predicate):
        return message_buffer.get_buffer().compare_range_adjacency_with_func2(
            start, end + 1,
            lambda target, compare: predicate(target, compare),
            iter_reverse=True,
        )

    @staticmethod
    def _find_difop_packet_index(message_buffer, start, end, predicate):
        return message_buffer.get_buffer().compare_range_adjacency_with_func3(
            start, end + 1,
            lambda element: predicate(element),
            iter_reverse=True,
        )

    @staticmethod
    def _azimuth_changed(target, compare) -> bool:
        t = target.get_payload_pretty(BpearlPayloadData)
        c = compare.get_payload_pretty(BpearlPayloadData)
        if t.get_packet_name() == BpearlPayloadData.DIFOP and c.get_packet_name() == BpearlPayloadData.DIFOP:
            return True
        ta = t.get_azimuth()
        ca = c.get_azimuth()
        if ta is None or ca is None:
            return False
        return abs(ta - ca) > 300

    @staticmethod
    def _is_connected_end_azimuth(message_buffer, end) -> bool:
        original_idx = 1
        next_idx = 1
        end_az = 0.0
        next_az = 0.0

        message_buffer.seek(end)
        while True:
            elem = message_buffer.get_buffer().get_current_element()
            payload = elem.get_payload_pretty(BpearlPayloadData)
            if payload.get_packet_name() != BpearlPayloadData.DIFOP:
                end_az = payload.get_azimuth() or 0
                break
            message_buffer.seek(end + original_idx)
            original_idx += 1

        message_buffer.seek(end + original_idx + next_idx)
        while True:
            elem = message_buffer.get_buffer().get_current_element()
            payload = elem.get_payload_pretty(BpearlPayloadData)
            if payload.get_packet_name() != BpearlPayloadData.DIFOP:
                next_az = payload.get_azimuth() or 0
                break
            message_buffer.seek(end + original_idx + next_idx)
            next_idx += 1

        return abs(end_az - next_az) < 300

    @staticmethod
    def _save_tmp_pcap(tmp_result_path: str, src_path: str, message_buffer,
                       start: int, end: int) -> str:
        message_buffer.get_buffer().start_marking(start)
        if end < 0:
            end = message_buffer.get_buffer().get_end_cursor()
        message_buffer.get_buffer().end_marking(end)
        picked = message_buffer.get_buffer().pick()

        test_idx = RsbpExtract._find_difop_packet_index(
            message_buffer, 0, start, RsbpExtract._is_difop_packet
        )
        if test_idx == -1:
            message_buffer.read_previous_file()
            first_last = message_buffer.get_buffer().get_first_file_last_packet_index()
            test_idx = RsbpExtract._find_difop_packet_index(
                message_buffer, 0, first_last, RsbpExtract._is_difop_packet
            )

        if test_idx != -1:
            element = message_buffer.get_buffer().get_element(test_idx)
            picked.append_element_left(element)

        normalized = tmp_result_path + os.path.basename(src_path)
        picked.save(normalized)
        return normalized

    @staticmethod
    def _is_difop_packet(element) -> bool:
        payload = element.get_payload_pretty(BpearlPayloadData)
        return payload.get_packet_name() == BpearlPayloadData.DIFOP

    @staticmethod
    def _upload(tmp_result_path: str, ctx: ExtractContext, src_file: str,
                upload_files, dst_storage, dst_path: str) -> None:
        if not upload_files:
            return

        original = os.path.basename(src_file).split(".")[0]
        zip_path = tmp_result_path + original + ".tar"

        ShellUtil(f"rm -rf {zip_path}", True).run()
        cmd = f"tar -cvf {zip_path} {tmp_result_path}{original}*"
        _, stderr = ShellUtil(cmd, True).run()
        if stderr and "tar: Removing leading `/'" not in stderr:
            return

        target = f"{dst_path}/{RsbpExtract._vehicle_id(ctx)}/{os.path.basename(zip_path)}"
        AppLogger.instance().info(f"Upload Result file : {zip_path} => {target}")
        dst_storage.upload(zip_path, target)
        RsbpExtract._delete_file(zip_path)

    @staticmethod
    def _vehicle_id(ctx: ExtractContext) -> str:
        return os.path.dirname(ctx.protocol.srcPath).split("/")[2]

    @staticmethod
    def _delete_tmp_files(files) -> None:
        for f in files:
            RsbpExtract._delete_file(f)

    @staticmethod
    def _delete_file(path: str) -> None:
        if os.path.exists(path):
            AppLogger.instance().info(f"delete {path}")
            os.remove(path)
