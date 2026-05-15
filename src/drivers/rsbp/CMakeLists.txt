cmake_minimum_required(VERSION 3.8.11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 14)
project(rsbp_converter)

# Set C++ standard
set(CMAKE_CXX_STANDARD 14)

# Find Python libraries
find_package(PythonLibs REQUIRED)
include_directories(${PYTHON_INCLUDE_DIRS})

# Find pybind11
set(pybind11_DIR "/usr/local/lib/python3.10/dist-packages/pybind11/share/cmake/pybind11")
find_package(pybind11 REQUIRED)

# Find Eigen
find_package(Eigen3 REQUIRED)
include_directories(${EIGEN3_INCLUDE_DIR})

# Find PCL
find_package(PCL COMPONENTS common visualization io QUIET REQUIRED)
add_definitions(${PCL_DEFINITIONS})
include_directories(${PCL_INCLUDE_DIRS})
link_directories(${PCL_LIBRARY_DIRS})

# Add subdirectory
add_subdirectory(rs_driver)
find_package(rs_driver REQUIRED)

# Include directories
include_directories(${rs_driver_INCLUDE_DIRS})

# Add compile time definitio of ENABLE_TRANSFORM
add_compile_definitions(ENABLE_TRANSFORM)

# Create Python module
pybind11_add_module(rsbp_converter rsbp_converter.cpp)

# Link Python libraries
target_link_libraries(rsbp_converter PRIVATE
    ${PYTHON_LIBRARIES}
    ${rs_driver_LIBRARIES}
    ${PCL_LIBRARIES}
)

# Copy shared library to upper directory
add_custom_command(TARGET rsbp_converter POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
    $<TARGET_FILE:rsbp_converter>
    ${CMAKE_CURRENT_SOURCE_DIR}
)
