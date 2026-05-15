#include <pybind11/pybind11.h>
#include <stdio.h>
#include <stdlib.h>
#include <chrono>

#include "novatel_edie/src/decoders/novatel/api/fileparser.hpp"
#include "novatel_edie/src/hw_interface/stream_interface/api/inputfilestream.hpp"
#include "novatel_edie/src/hw_interface/stream_interface/api/outputfilestream.hpp"
#include "novatel_edie/src/version.h"

namespace py = pybind11;

using namespace std;
using namespace novatel::edie;
using namespace novatel::edie::oem;

class IMUConverter {
private:
  std::string sJsonDB;
  std::string sEncodeFormat = "ASCII";
  std::string sInFilePath;
  std::string sPrefixFilePath;
public:
  IMUConverter(const pybind11::dict& params) 
    : sJsonDB(params["sJsonDB"].cast<std::string>()),
      sEncodeFormat(params["sEncodeFormat"].cast<std::string>()),
      sInFilePath(params["sInFilePath"].cast<std::string>()),
      sPrefixFilePath(params["sPrefixFilePath"].cast<std::string>()) 
  {
  }

  void start() {
    Logger::InitLogger();
    std::shared_ptr<spdlog::logger> pclLogger = Logger::RegisterLogger("converter");
    pclLogger->set_level(spdlog::level::debug);
    Logger::AddConsoleLogging(pclLogger);

    // pclLogger->info("Decoder library information:\n{}", caPrettyPrint);

    ENCODEFORMAT eEncodeFormat = StringToEncodeFormat(sEncodeFormat);

    JsonReader clJsonDb;
    // pclLogger->info("Loading Database...");
    auto tStart = chrono::high_resolution_clock::now();
    clJsonDb.LoadFile(sJsonDB);
    // pclLogger->info("Done in {}ms", chrono::duration_cast<chrono::milliseconds>(chrono::high_resolution_clock::now() - tStart).count());

    // Setup timers
    auto tLoop = chrono::high_resolution_clock::now();

    FileParser clFileParser(&clJsonDb);
    clFileParser.SetLoggerLevel(spdlog::level::debug);

    Filter clFilter;
    clFilter.SetLoggerLevel(spdlog::level::debug);

    STATUS eStatus = STATUS::UNKNOWN;

    MetaDataStruct stMetaData;
    MessageDataStruct stMessageData;

    clFileParser.SetFilter(&clFilter);
    clFileParser.SetEncodeFormat(eEncodeFormat);

    // Initialize FS structures and buffers
    ReadDataStructure stReadData;
    unsigned char acIFSReadBuffer[MAX_ASCII_MESSAGE_LENGTH];
    stReadData.cData = reinterpret_cast<char*>(acIFSReadBuffer);
    stReadData.uiDataSize = sizeof(acIFSReadBuffer);

    // Setup filestreams
    InputFileStream clIFS(sInFilePath.c_str());

    // sInFilePath의 경로를 제외한 파일명을 sInFileName에 저장
    std::string sInFileName = sInFilePath.substr(sInFilePath.find_last_of("/\\") + 1);

    std::string sOutputPath = sPrefixFilePath + sInFileName;

    OutputFileStream clConvertedLogsOFS(sOutputPath.append(".").append(sEncodeFormat).c_str());

    if (!clFileParser.SetStream(&clIFS))
    {
        pclLogger->error("Input stream could not be set.  The stream is either unavailable or exhausted.");
    }

    uint32_t uiCompleteMessages = 0;
    uint32_t uiCounter = 0;
    tStart = chrono::high_resolution_clock::now();
    tLoop = chrono::high_resolution_clock::now();

    while (eStatus != STATUS::STREAM_EMPTY)
    {
        try
        {
            eStatus = clFileParser.Read(stMessageData, stMetaData);
            if (eStatus == STATUS::SUCCESS)
            {
                clConvertedLogsOFS.WriteData(reinterpret_cast<char*>(stMessageData.pucMessage), stMessageData.uiMessageLength);
                stMessageData.pucMessage[stMessageData.uiMessageLength] = '\0';
                // pclLogger->info("Encoded: ({}) {}", stMessageData.uiMessageLength, reinterpret_cast<char*>(stMessageData.pucMessage));
                uiCompleteMessages++;
            }
        }
        catch (std::exception& e)
        {
            pclLogger->error("Exception thrown:  {}, {} \n{}\n", __DATE__, __TIME__, e.what());
            exit(-1);
        }

        if (chrono::duration_cast<chrono::milliseconds>(chrono::high_resolution_clock::now() - tLoop).count() > 1000)
        {
            uiCounter++;
            pclLogger->info("{}% {} logs/s", clFileParser.GetPercentRead(), uiCompleteMessages / uiCounter);
            tLoop = chrono::high_resolution_clock::now();
        }
    }
    // pclLogger->info("Converted {} logs in {}s from {}", uiCompleteMessages,
    //                 (chrono::duration_cast<chrono::milliseconds>(chrono::high_resolution_clock::now() - tStart).count() / 1000.0),
    //                 sInFilePath.c_str());

    Logger::Shutdown();
  }
};

PYBIND11_MODULE(imu_converter, m) {
  py::class_<IMUConverter>(m, "IMUConverter")
    .def(py::init<const pybind11::dict&>())
    .def("start", &IMUConverter::start);
}