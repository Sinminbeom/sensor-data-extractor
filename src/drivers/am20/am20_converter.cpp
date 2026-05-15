#include <pybind11/pybind11.h>
#include <gst/gst.h>
#include <gst/app/gstappsrc.h>
#include <string>
#include <vector>
#include <iostream>
#include <cstdint>
#include <thread>
#include <mutex>
// #include <future>

namespace py = pybind11;

class AM20Converter {
private:
    GstElement* pipeline;
    GstElement* appsrc;
    GstElement* tsdemux;
    GstElement* h264parse;
    GstElement* nvv4l2decoder;
    GstElement* nvvideoconvert;
    GstElement* jpegenc;
    GstElement* nvjpegenc;
    GstElement* multifilesink;

    GstBus *bus;
    GMainLoop* loop;

    static std::string tmpResultSavedPath;
    static std::string originalFilename;
    static std::string dstPath;
    static std::string startTime;
    static guint frameNumber;

    std::vector<GstBuffer*> buffers;

    std::mutex myMutex;

    std::future<void> myFuture;

    py::object callback;
public:
    AM20Converter(const pybind11::dict& params)
    {
        createPipeline();
    }

    void registerPythonCallback(py::object _pythonCallback){
        callback = _pythonCallback;
    }

    void createPipeline() {
        gst_init(nullptr, nullptr);

        pipeline = gst_pipeline_new("dynamic-pipeline");
        appsrc = gst_element_factory_make("appsrc", "appsrc");
        tsdemux = gst_element_factory_make("tsdemux", "tsdemux");
        h264parse = gst_element_factory_make("h264parse", "h264parse");
        nvv4l2decoder = gst_element_factory_make("nvv4l2decoder", "nvv4l2decoder");
        nvvideoconvert = gst_element_factory_make("nvvideoconvert", "nvvideoconvert");
        jpegenc = gst_element_factory_make("jpegenc", "jpegenc");
        multifilesink = gst_element_factory_make("multifilesink", "multifilesink");

        loop = g_main_loop_new(nullptr, FALSE);
        addSignalWatch();
    }

    void addSignalWatch() {
        bus = gst_pipeline_get_bus(GST_PIPELINE(pipeline));
        gst_bus_add_signal_watch(bus);
        g_signal_connect_data(bus, "message", G_CALLBACK(busCallback), loop, NULL, (GConnectFlags) 0);
    }

    void clear() {
        std::lock_guard<std::mutex> guard(myMutex);
        g_main_loop_quit (loop);
        setGstStateStop();
        frameNumber = 0;

        if (callback){
            callback(tmpResultSavedPath, originalFilename, dstPath, startTime);
        }
    }

    static gboolean busCallback(GstBus *bus, GstMessage *message, gpointer data) {
        AM20Converter* converter = static_cast<AM20Converter*>(data);
        GMainLoop* loop = static_cast<GMainLoop*>(data);

        switch (GST_MESSAGE_TYPE (message)) {
            case GST_MESSAGE_ERROR:{
                GError *err;
                gchar *debug;

                gst_message_parse_error (message, &err, &debug);
                g_print ("Error: %s\n", err->message);
                g_error_free (err);
                g_free (debug);

                converter->clear();
                break;
            }
            case GST_MESSAGE_EOS:
                converter->clear();
                break;
            default:
                break;
        }

        return TRUE;
    }

    void addElement() {
        gst_bin_add_many(GST_BIN (pipeline), appsrc, tsdemux, h264parse, nvv4l2decoder, nvvideoconvert, jpegenc, multifilesink, NULL);
    }

    static void linkElement(GstElement *srcElement, GstPad *sourcePad, GstElement *sinkElement) {
        GstPad *sinkPad = gst_element_get_static_pad(sinkElement, "sink");
        gst_pad_link(sourcePad, sinkPad);
        gst_object_unref(sinkPad);
    }

    void linkElements() {
        gst_element_link(appsrc, tsdemux);
        g_signal_connect_data(tsdemux, "pad-added", G_CALLBACK(linkElement), h264parse, NULL, (GConnectFlags) 0);
        gst_element_link(h264parse, nvv4l2decoder);
        gst_element_link(nvv4l2decoder, nvvideoconvert);
        gst_element_link(nvvideoconvert, jpegenc);
        gst_element_link(jpegenc, multifilesink);
    }

    void setProperty(char* _tmpResultSavedPath, char* _originalFilename, char* _dstPath, char* _startTime) {
        g_object_set(appsrc, "format", GST_FORMAT_TIME, NULL);

        tmpResultSavedPath = _tmpResultSavedPath;
        originalFilename = _originalFilename;
        dstPath = _dstPath;
        startTime = _startTime;
    }

    static GstPadProbeReturn addNanosenodsAndFrameToLocation(GstPad *pad, GstPadProbeInfo *info, gpointer user_data) {
        GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER(info);
        GstClockTime timestamp = GST_BUFFER_PTS(buffer);
        GstElement *multifilesink = GST_ELEMENT(user_data);

        // nanoseconds to seconds
        gdouble timestamp_in_seconds = (gdouble)timestamp / GST_SECOND;

        frameNumber++;
        std::string location;
        location.append(tmpResultSavedPath)
                .append(originalFilename)
                .append("_")
                .append(std::to_string(frameNumber))
                .append(".jpg");

        g_object_set(multifilesink, "location", location.c_str(), NULL);

        return GST_PAD_PROBE_OK;

    }

    void addProbe() {
        GstPad* sinkPad = gst_element_get_static_pad(multifilesink, "sink");
        gst_pad_add_probe(sinkPad, GST_PAD_PROBE_TYPE_BUFFER, addNanosenodsAndFrameToLocation, multifilesink, NULL);
        gst_object_unref(sinkPad);
    }

    gboolean sendPacket(gpointer user_data) {
        for (auto buffer : buffers) {

            GstFlowReturn ret = gst_app_src_push_buffer(GST_APP_SRC(appsrc), buffer);
            if (ret != GST_FLOW_OK) {
                gst_app_src_end_of_stream(GST_APP_SRC(appsrc));
                return FALSE;
            }
        }
        buffers.clear();
        gst_app_src_end_of_stream(GST_APP_SRC(appsrc));
        return FALSE;
    }

    void addIdle() {
        g_idle_add([](gpointer user_data) -> gboolean {
            AM20Converter* converter = static_cast<AM20Converter*>(user_data);
            return converter->sendPacket(user_data);
        }, this);
    }

    void appendBuffer(char* _buffer, char* _nanosec, int buffer_size) {
        std::string decimal_string(_nanosec);
        long double decimal_value;

        try {
            decimal_value = std::stold(decimal_string);
        } catch (const std::invalid_argument& e) {
            std::cerr << "Invalid argument: " << e.what() << std::endl;
            return;
        } catch (const std::out_of_range& e) {
            std::cerr << "Out of range: " << e.what() << std::endl;
            return;
        }

        GstBuffer* buffer = gst_buffer_new_allocate(nullptr, buffer_size, nullptr);
        gst_buffer_fill(buffer, 0, _buffer, buffer_size);
        GST_BUFFER_PTS(buffer) = decimal_value;
        buffers.push_back(buffer);
    }

    void setGstStatePlay() {
        gst_element_set_state(pipeline, GST_STATE_PLAYING);
    }

    void setGstStatePause() {
        gst_element_set_state(pipeline, GST_STATE_PAUSED);
    }

    void setGstStateStop() {
        gst_element_set_state(pipeline, GST_STATE_NULL);
    }

    void start() {
        myFuture = std::async(std::launch::async, run);
    }

    void join() {
        myFuture.get();
    }

    void run() {
        try {
            g_main_loop_run(loop);
        } catch (const std::exception& e) {
            std::cerr << "Exception caught: " << e.what() << std::endl;
            return;
        }
    }
};

PYBIND11_MODULE(am20_converter, m) {
  py::class_<AM20Converter>(m, "AM20Converter")
    .def(py::init<const pybind11::dict&>())
    .def("registerPythonCallback", &AM20Converter::registerPythonCallback, "A function that starts the lidar")
    .def("setProperty", &AM20Converter::setProperty, "A function that starts the lidar")
    .def("setProperty", &AM20Converter::setProperty, "A function that starts the lidar");
    
    // .def("start", &AM20Converter::start, "A function that starts the lidar")
}
