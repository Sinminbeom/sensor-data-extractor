cmake_minimum_required(VERSION 3.8.11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 14)
project(at128_converter)

# Set C++ standard
set(CMAKE_CXX_STANDARD 14)
# set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")

# Find Python libraries
find_package(PythonLibs REQUIRED)
include_directories(${PYTHON_INCLUDE_DIRS})

# Find pybind11
set(pybind11_DIR "/usr/local/lib/python3.10/dist-packages/pybind11/share/cmake/pybind11")
find_package(pybind11 REQUIRED)

find_package(PCL COMPONENTS common visualization io QUIET REQUIRED)
include_directories(${PCL_INCLUDE_DIRS})
link_directories(${PCL_LIBRARY_DIRS})

# Add subdirectory
add_subdirectory(HesaiLidar_SDK_2.0)

# Include directories
set(HESAI_SDK ${CMAKE_CURRENT_SOURCE_DIR}/HesaiLidar_SDK_2.0)
set(HESAI_BIN ${CMAKE_CURRENT_BINARY_DIR}/HesaiLidar_SDK_2.0)
include_directories(
    ${HESAI_SDK}/libhesai
    ${HESAI_SDK}/libhesai/Lidar
    ${HESAI_SDK}/libhesai/UdpParser
    ${HESAI_SDK}/libhesai/UdpParser/include
    ${HESAI_SDK}/libhesai/UdpParser/src
    ${HESAI_SDK}/libhesai/UdpProtocol
    ${HESAI_SDK}/libhesai/Source/include
    ${HESAI_SDK}/libhesai/Container/include
    ${HESAI_SDK}/libhesai/Container/src
    ${HESAI_SDK}/libhesai/UdpParserGpu
    ${HESAI_SDK}/libhesai/UdpParserGpu/include
    ${HESAI_SDK}/libhesai/UdpParserGpu/src
    ${HESAI_SDK}/libhesai/PtcClient/include
    ${HESAI_SDK}/libhesai/PtcParser
    ${HESAI_SDK}/libhesai/PtcParser/src
    ${HESAI_SDK}/libhesai/PtcParser/include
    ${HESAI_SDK}/libhesai/Logger/include
    ${HESAI_SDK}/libhesai/include
    ${HESAI_SDK}/driver
    ${HESAI_SDK}/third_party
    ${HESAI_BIN}
)

# Create Python module
pybind11_add_module(at128_converter at128_converter.cpp)

# Link Python libraries
target_link_libraries(at128_converter PRIVATE
    ${PYTHON_LIBRARIES}
    source_lib
    container_lib
    ptcClient_lib
    ptcParser_lib
    log_lib
    ${PCL_LIBRARIES}
)

# Copy shared library to upper directory
add_custom_command(TARGET at128_converter POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
    $<TARGET_FILE:at128_converter>
    ${CMAKE_CURRENT_SOURCE_DIR}
)

