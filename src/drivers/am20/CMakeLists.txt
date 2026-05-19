cmake_minimum_required(VERSION 3.15)

project(am20_converter)

set(CMAKE_CXX_STANDARD 17)
find_package(PkgConfig REQUIRED)

# GStreamer
pkg_check_modules(GSTREAMER REQUIRED gstreamer-1.0 gstreamer-app-1.0)

# Python — venv interpreter 사용 (cmake 호출 시 PYTHON_EXECUTABLE 지정 가능)
find_package(Python COMPONENTS Interpreter Development REQUIRED)

# pybind11 — venv 의 site-packages 에서 cmake dir 자동 탐지
execute_process(
    COMMAND ${Python_EXECUTABLE} -c "import pybind11; print(pybind11.get_cmake_dir())"
    OUTPUT_VARIABLE pybind11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
find_package(pybind11 CONFIG REQUIRED)

#including GStreamer header files directory
include_directories(
        .
        ${GLIB_INCLUDE_DIRS}
        ${GSTREAMER_INCLUDE_DIRS}
)

#linking GStreamer library directory
link_directories(
        ${GLIB_LIBRARY_DIRS}
        ${GSTREAMER_LIBRARY_DIRS}
)

# GPU 변형 — NVIDIA DeepStream (nvv4l2decoder + nvvideoconvert) 사용
pybind11_add_module(am20_converter am20_converter.cpp)
target_link_libraries(am20_converter PRIVATE ${GSTREAMER_LIBRARIES})
add_custom_command(TARGET am20_converter POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
    $<TARGET_FILE:am20_converter>
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# CPU 변형 — avdec_h264 + videoconvert (NVIDIA GPU 미사용)
pybind11_add_module(am20_converter_cpu am20_converter_cpu.cpp)
target_link_libraries(am20_converter_cpu PRIVATE ${GSTREAMER_LIBRARIES})
add_custom_command(TARGET am20_converter_cpu POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
    $<TARGET_FILE:am20_converter_cpu>
    ${CMAKE_CURRENT_SOURCE_DIR}
)