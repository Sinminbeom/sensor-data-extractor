import platform
from collections import deque
from decimal import Decimal

# Linux/CUDA(deepstream) 환경에서만 gi 로드
if platform.system() != "Windows":
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import GLib, Gst
    except Exception:
        Gst = None  # type: ignore
        GLib = None  # type: ignore
# AM20 카메라(MPEG2-TS over RTP, H.265) → PNG frame 추출용 GStreamer pipeline 래퍼.
# pipeline 구성:
#   appsrc → rtpmp2tdepay → tsdemux → h265parse → nvv4l2decoder → nvvideoconvert → pngenc → multifilesink
# (Deepstream/nvv4l2decoder/nvvideoconvert는 GPU 가속 element. CPU only 환경용 대체 pipeline도 코드에 보존.)
# 클래스명 cGstreamer → GstreamerExtractorPipeline (역할 명확화).
class GstreamerExtractorPipeline:
    def __init__(self, tmp_result_saved_path: str, original_filename: str) -> None:
        self.tmp_result_saved_path = tmp_result_saved_path
        self.original_filename = original_filename
        self.frame_number = 0

        Gst.init(None)

        self.pipeline = None
        self.appsrc = None
        self.rtpmp2tdepay = None
        self.tsdemux = None
        self.h265parse = None
        self.nvv4l2decoder = None
        self.nvvideoconvert = None
        self.pngenc = None
        self.multifilesink = None

        # CPU only fallback
        self.avdec_h265 = None
        self.videoconvert = None

        self.bus = None
        self.buffers: deque = deque()

        self._create_pipeline()
        self._set_property()
        self._add_element()
        self._link()

    def _create_pipeline(self) -> None:
        self.pipeline = Gst.Pipeline.new("dynamic-pipeline")
        self.appsrc = Gst.ElementFactory.make("appsrc", "appsrc")
        self.rtpmp2tdepay = Gst.ElementFactory.make("rtpmp2tdepay", "rtpmp2tdepay")
        self.tsdemux = Gst.ElementFactory.make("tsdemux", "tsdemux")
        self.h265parse = Gst.ElementFactory.make("h265parse", "h265parse")
        self.nvv4l2decoder = Gst.ElementFactory.make("nvv4l2decoder", "nvv4l2decoder")
        self.nvvideoconvert = Gst.ElementFactory.make("nvvideoconvert", "nvvideoconvert")
        self.pngenc = Gst.ElementFactory.make("pngenc", "pngenc")
        self.multifilesink = Gst.ElementFactory.make("multifilesink", "multifilesink")

    def _create_non_deepstream_pipeline(self) -> None:
        self.pipeline = Gst.Pipeline.new("dynamic-pipeline")
        self.appsrc = Gst.ElementFactory.make("appsrc", "appsrc")
        self.rtpmp2tdepay = Gst.ElementFactory.make("rtpmp2tdepay", "rtpmp2tdepay")
        self.tsdemux = Gst.ElementFactory.make("tsdemux", "tsdemux")
        self.h265parse = Gst.ElementFactory.make("h265parse", "h265parse")
        self.avdec_h265 = Gst.ElementFactory.make("avdec_h265", "avdec_h265")
        self.videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        self.pngenc = Gst.ElementFactory.make("pngenc", "pngenc")
        self.multifilesink = Gst.ElementFactory.make("multifilesink", "multifilesink")

    def _set_property(self) -> None:
        caps = Gst.Caps.from_string(
            "application/x-rtp,media=video,encoding-name=MP2T,clock-rate=90000,payload=33"
        )
        self.appsrc.set_property("caps", caps)
        self.appsrc.set_property("format", Gst.Format.TIME)

    def _add_element(self) -> None:
        for element in [
            self.appsrc,
            self.rtpmp2tdepay,
            self.tsdemux,
            self.h265parse,
            self.nvv4l2decoder,
            self.nvvideoconvert,
            self.pngenc,
            self.multifilesink,
        ]:
            self.pipeline.add(element)

    def _link(self) -> None:
        self.appsrc.link(self.rtpmp2tdepay)
        self.rtpmp2tdepay.link(self.tsdemux)
        self.tsdemux.connect("pad-added", self._link_elements, self.h265parse)
        self.h265parse.link(self.nvv4l2decoder)
        self.nvv4l2decoder.link(self.nvvideoconvert)
        self.nvvideoconvert.link(self.pngenc)
        self.pngenc.link(self.multifilesink)

    def _non_deepstream_link(self) -> None:
        self.appsrc.link(self.rtpmp2tdepay)
        self.rtpmp2tdepay.link(self.tsdemux)
        self.tsdemux.connect("pad-added", self._link_elements, self.h265parse)
        self.h265parse.link(self.avdec_h265)
        self.avdec_h265.link(self.videoconvert)
        self.videoconvert.link(self.pngenc)
        self.pngenc.link(self.multifilesink)

    @staticmethod
    def _link_elements(element, source_pad, sink_element) -> None:
        sink_pad = sink_element.get_static_pad("sink")
        source_pad.link(sink_pad)

    def add_probe(self):
        sink_pad = self.multifilesink.get_static_pad("sink")
        return sink_pad.add_probe(
            Gst.PadProbeType.BUFFER, self._add_nanosec_and_frame_to_location, self.multifilesink
        )

    def remove_probe(self, probe_id) -> None:
        sink_pad = self.multifilesink.get_static_pad("sink")
        sink_pad.remove_probe(probe_id)

    def _add_nanosec_and_frame_to_location(self, pad, info, data):
        buffer = Gst.PadProbeInfo.get_buffer(info)
        timestamp = buffer.pts
        multifilesink = data
        timestamp_in_seconds = Decimal(timestamp) / Decimal("1000000000")

        if Decimal("2") <= timestamp_in_seconds < Decimal("3"):
            self.frame_number += 1
            location = (
                f"{self.tmp_result_saved_path}{self.original_filename}_{self.frame_number}.png"
            )
            multifilesink.set_property("location", location)
            return Gst.PadProbeReturn.OK
        elif timestamp_in_seconds >= Decimal("3"):
            return Gst.PadProbeReturn.REMOVE
        else:
            return Gst.PadProbeReturn.DROP

    def add_idle(self) -> None:
        GLib.idle_add(self._send_packet)

    def _send_packet(self) -> bool:
        for buffer in self.buffers:
            ret = self.appsrc.emit("push-buffer", buffer)
            if ret != Gst.FlowReturn.OK:
                self.appsrc.emit("end-of-stream")
                return False

        self.appsrc.emit("end-of-stream")
        return False

    def _bus_callback(self, bus, message, loop) -> bool:
        msg_type = message.type
        if msg_type == Gst.MessageType.EOS:
            loop.quit()
        elif msg_type == Gst.MessageType.ERROR:
            return False
        return True

    def _add_signal_watch(self, loop) -> None:
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._bus_callback, loop)

    def run(self) -> None:
        self.pipeline.set_state(Gst.State.PLAYING)
        loop = GLib.MainLoop()
        self._add_signal_watch(loop)
        loop.run()

    def append_buffer(self, payload: bytes, nanosec: int) -> None:
        buffer = Gst.Buffer.new_allocate(None, len(payload), None)
        buffer.fill(0, payload)
        buffer.pts = int(nanosec)
        self.buffers.append(buffer)

    def _unref_buffers(self) -> None:
        for buffer in self.buffers:
            buffer.remove_all_memory()

    def unref(self) -> None:
        for element in [
            self.appsrc,
            self.rtpmp2tdepay,
            self.tsdemux,
            self.h265parse,
            self.nvvideoconvert,
            self.nvv4l2decoder,
            self.pngenc,
            self.multifilesink,
            self.bus,
        ]:
            if element is not None:
                element.unref()
        self._unref_buffers()
        self.pipeline.set_state(Gst.State.NULL)

    def non_deepstream_unref(self) -> None:
        for element in [
            self.appsrc,
            self.rtpmp2tdepay,
            self.tsdemux,
            self.h265parse,
            self.avdec_h265,
            self.videoconvert,
            self.pngenc,
            self.multifilesink,
            self.bus,
        ]:
            if element is not None:
                element.unref()
        self._unref_buffers()
        self.pipeline.set_state(Gst.State.NULL)
