#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <pcl/common/io.h>
#include <pcl/io/pcd_io.h>
#include "rs_driver/api/lidar_driver.hpp"
#include <rs_driver/msg/pcl_point_cloud_msg.hpp>

namespace py = pybind11;
using namespace robosense::lidar;

typedef PointXYZIRT PointT;
typedef PointCloudT<PointT> PointCloudMsg;

class RSBPConverter {
private:
  LidarDriver<PointCloudMsg>& _driver;

  SyncQueue<std::shared_ptr<PointCloudMsg>> free_cloud_queue;
  SyncQueue<std::shared_ptr<PointCloudMsg>> stuffed_cloud_queue;

  std::thread _handle_thread;
  bool _is_exit = false;

  std::mutex _frame_mutex;
  std::string lidar_name;
  std::string timestamp;
  std::string src_path;
  std::string dst_path;
  int msop_port;
  int difop_port;
  std::list<std::string> dst_path_list;
  py::function callback;

public:
  RSBPConverter(const pybind11::dict& params)
    : _driver(*new LidarDriver<PointCloudMsg>())
  {
    lidar_name = params["lidarName"].cast<std::string>();
    timestamp = params["timestamp"].cast<std::string>();
    src_path = params["srcPath"].cast<std::string>();
    dst_path = params["dstPath"].cast<std::string>();
    msop_port = params["msopPort"].cast<int>();
    difop_port = params["difopPort"].cast<int>();

    RSDriverParam param;
    param.input_param.pcap_repeat = false;
    param.decoder_param.dense_points = true;
    param.input_type = InputType::PCAP_FILE;
    param.lidar_type = LidarType::RSBP;
    param.input_param.pcap_path = src_path;
    param.input_param.msop_port = msop_port;
    param.input_param.difop_port = difop_port;
    param.decoder_param.wait_for_difop = false;
    param.decoder_param.use_lidar_clock = true;

    if (params.contains("extrinsic")) {
      if (params["extrinsic"].contains("x"))
        param.decoder_param.transform_param.x = params["extrinsic"]["x"].cast<double>();
      if (params["extrinsic"].contains("y"))
        param.decoder_param.transform_param.y = params["extrinsic"]["y"].cast<double>();
      if (params["extrinsic"].contains("z"))
        param.decoder_param.transform_param.z = params["extrinsic"]["z"].cast<double>();
      if (params["extrinsic"].contains("roll"))
        param.decoder_param.transform_param.roll = params["extrinsic"]["roll"].cast<double>();
      if (params["extrinsic"].contains("pitch"))
        param.decoder_param.transform_param.pitch = params["extrinsic"]["pitch"].cast<double>();
      if (params["extrinsic"].contains("yaw"))
        param.decoder_param.transform_param.yaw = params["extrinsic"]["yaw"].cast<double>();
    }

    _driver.regPointCloudCallback(
      [&] {
        std::shared_ptr<PointCloudMsg> msg = free_cloud_queue.pop();
        if (msg.get() != NULL)
          return msg;

        return std::make_shared<PointCloudMsg>();
      },
      [&](std::shared_ptr<PointCloudMsg> msg) {
        stuffed_cloud_queue.push(msg);
      }
    );

    _driver.regExceptionCallback(
      [](const Error& code) {
        // std::cerr << "Error code: " << code.toString() << std::endl;
      }
    );

    _driver.init(param);
  }

  ~RSBPConverter() {
    delete &_driver;
  }

  void start() {
    _driver.start();
    _handle_thread = std::thread([&]() { process_points(); });
  }

  void stop() {
    _driver.stop();
    _is_exit = true;
    // _handle_thread.join();
  }

  void RegisterCallback(py::function _callback) {
    this->callback = _callback;
  }

  std::list<std::string> GetDstPathList() {
    return dst_path_list;
  }

  void process_points(void) {
    while (!_is_exit) {
      std::shared_ptr<PointCloudMsg> msg = stuffed_cloud_queue.popWait();
      if (msg.get() == NULL) {
        py::gil_scoped_acquire acquire;
        callback();
        continue; 
      }

      _frame_mutex.lock();

      std::string pcdFilePath = dst_path + lidar_name + "_" + timestamp + "_" + std::to_string(msg->seq) + "_" + std::to_string(msg->points[0].timestamp) + ".bin";

      pcl::PCDWriter writer;
      writer.writeBinaryCompressed(pcdFilePath, *msg);
      // writer.writeASCII(pcdFilePath, *msg, 16);
      dst_path_list.push_back(pcdFilePath);
      // printf("Write binary PCD file : %s\n", pcdFilePath.c_str());

      _frame_mutex.unlock();

      free_cloud_queue.push(msg);
    }
  }
};

PYBIND11_MODULE(rsbp_converter, m) {
  py::class_<RSBPConverter>(m, "RSBPConverter")
    .def(py::init<const pybind11::dict&>())
    .def("start", &RSBPConverter::start)
    .def("stop", &RSBPConverter::stop)
    .def("RegisterCallback", &RSBPConverter::RegisterCallback)
    .def("GetDstPathList", &RSBPConverter::GetDstPathList);
}