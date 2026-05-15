#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "hesai_lidar_sdk.hpp"
#define PCL_NO_PRECOMPILE
#include <pcl/point_types.h>
#include <pcl/visualization/pcl_visualizer.h>
#include <pcl/io/pcd_io.h>
#include <pcl/io/ply_io.h>

namespace py = pybind11;

struct PointXYZIT {
  PCL_ADD_POINT4D
  float intensity;
  double timestamp;
  uint16_t ring;
  EIGEN_MAKE_ALIGNED_OPERATOR_NEW
} EIGEN_ALIGN16;

POINT_CLOUD_REGISTER_POINT_STRUCT(
    PointXYZIT,
    (float, x, x)(float, y, y)(float, z, z)(float, intensity, intensity)
    (double, timestamp, timestamp)(std::uint16_t, ring, ring))

class At128Converter {
private:
  HesaiLidarSdk<PointXYZIT>& _driver;
  std::mutex _frame_mutex;

  std::string lidar_name;
  std::string timestamp;
  std::string src_path;
  std::string dst_path;
  std::list<std::string> dst_path_list;

public:
  At128Converter(const pybind11::dict& params)
    : _driver(*new HesaiLidarSdk<PointXYZIT>()),
      lidar_name(params["lidarName"].cast<std::string>()),
      timestamp(params["timestamp"].cast<std::string>()),
      src_path(params["srcPath"].cast<std::string>()),
      dst_path(params["dstPath"].cast<std::string>())
  {
    DriverParam param;

    // assign param
    param.input_param.source_type = DATA_FROM_PCAP;
    param.input_param.ptc_mode = PtcMode::tcp;
    param.input_param.ptc_port = 9347;
    param.input_param.pcap_path = src_path;
    param.input_param.correction_file_path = "./src/drivers/at128/correction/angle_correction/AT128E2X_Angle Correction File.dat";
    param.input_param.firetimes_path = "./src/drivers/at128/correction/firetime_correction/AT128E2X_Firetime Correction File.csv";

    if (params.contains("extrinsic")) {
      param.decoder_param.transform_param.x = params["extrinsic"]["x"].cast<double>();
      param.decoder_param.transform_param.y = params["extrinsic"]["y"].cast<double>();
      param.decoder_param.transform_param.z = params["extrinsic"]["z"].cast<double>();
      param.decoder_param.transform_param.roll = params["extrinsic"]["roll"].cast<double>();
      param.decoder_param.transform_param.pitch = params["extrinsic"]["pitch"].cast<double>();
      param.decoder_param.transform_param.yaw = params["extrinsic"]["yaw"].cast<double>();
    }

    py::gil_scoped_release release;
    _driver.Init(param);
    py::gil_scoped_acquire acquire;

    // Assign the callback function
    _driver.RegRecvCallback([&](const LidarDecodedFrame<PointXYZIT>& frame) {
      std::lock_guard<std::mutex> lock(_frame_mutex);
      pcl::PointCloud<PointXYZIT>::Ptr pcl_pointcloud(new pcl::PointCloud<PointXYZIT>);
      if (frame.points_num == 0) return;
      pcl_pointcloud->clear();
      pcl_pointcloud->resize(frame.points_num);
      pcl_pointcloud->points.assign(frame.points, frame.points + frame.points_num);
      pcl_pointcloud->height = 1;
      pcl_pointcloud->width = frame.points_num;
      pcl_pointcloud->is_dense = false;

      std::string file_name4 = dst_path + lidar_name + "_" + timestamp + "_" + std::to_string(frame.frame_index) + "_" + std::to_string(frame.points[0].timestamp) + "_compress" + ".bin";

      // ASCII 파일저장
      // pcl::PCDWriter writer;
      // int precision = 16;
      // writer.writeASCII(file_name4, *pcl_pointcloud, precision);

      // bin compressed 파일저장
      pcl::io::savePCDFileBinaryCompressed(file_name4, *pcl_pointcloud);
      dst_path_list.push_back(file_name4);
      // printf("frame:%d points:%u packet:%d start time:%lf end time:%lf\n",frame.frame_index, frame.points_num, frame.packet_num, frame.points[0].timestamp, frame.points[frame.points_num - 1].timestamp) ;
      // printf("Write binary PCD file : %s\n", file_name4.c_str());
    });
  }
  ~At128Converter() {
    // printf("Destructor\n");
    delete &_driver;
  }

  void start() {
    // Start the process thread
    _driver.Start();
  }

  void stop() {
    _driver.Stop();
  }

  bool GetIsEndSavePcd() {
    return _driver.GetIsEndSavePcd();
  }

  std::list<std::string> GetDstPathList() {
    return dst_path_list;
  }

};


PYBIND11_MODULE(at128_converter, m) {
  py::class_<At128Converter>(m, "At128Converter")
    .def(py::init<const pybind11::dict&>())
    .def("start", &At128Converter::start, "A function that starts the lidar")
    .def("stop", &At128Converter::stop, "A function that stops the lidar")
    .def("GetDstPathList", &At128Converter::GetDstPathList, "A function that stops the lidar")
    .def("GetIsEndSavePcd", &At128Converter::GetIsEndSavePcd, "A function that stops the lidar");
}
