cmake_minimum_required(VERSION 3.10)

project(am20_converter) #Project name

set(CMAKE_CXX_STANDARD 14) #setting C++ 14 standard
find_package(PkgConfig) #finding pkg-config is a helper tool

#using pkg-config to getting Gstreamer
pkg_check_modules(GSTREAMER REQUIRED gstreamer-1.0 gstreamer-app-1.0)

# Find Python libraries
find_package(PythonLibs REQUIRED)
include_directories(${PYTHON_INCLUDE_DIRS})

# Find pybind11
set(pybind11_DIR "/usr/local/lib/python3.10/dist-packages/pybind11/share/cmake/pybind11")
find_package(pybind11 REQUIRED)

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

# Create Python module
pybind11_add_module(${PROJECT_NAME} am20_converter.cpp)

# add_library(${PROJECT_NAME} SHARED
#             src/cGstreamer.cpp)

# add_library(${PROJECT_NAME} SHARED
#             src/test7.cpp)

#building target executable
# add_executable(${PROJECT_NAME} src/main.cpp src/cGstreamer.cpp)

#linking Gstreamer library with target executable
target_link_libraries(${PROJECT_NAME} PRIVATE ${GSTREAMER_LIBRARIES})

# Copy shared library to upper directory
add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
    $<TARGET_FILE:am20_converter>
    ${CMAKE_CURRENT_SOURCE_DIR}
)