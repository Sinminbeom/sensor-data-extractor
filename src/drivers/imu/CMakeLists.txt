cmake_minimum_required(VERSION 3.14)
project(imu_converter VERSION 3.1.0)

# 컴파일 명령어 출력 및 빌드 설정
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_VERBOSE_MAKEFILE OFF)
set(CMAKE_BUILD_TYPE Release)

# C++ 표준 설정
set(CMAKE_CXX_STANDARD 20)

# 프로젝트에서 사용할 라이브러리 설정
set(PROJECT_LINK_LIBS common novatel stream_interface)

# Python 라이브러리 찾기
find_package(PythonLibs REQUIRED)
include_directories(${PYTHON_INCLUDE_DIRS})

# pybind11 찾기
set(pybind11_DIR "/usr/local/lib/python3.10/dist-packages/pybind11/share/cmake/pybind11")
find_package(pybind11 REQUIRED)

# 서브디렉토리 추가
add_subdirectory(novatel_edie)

# Include 디렉토리 설정
set(NOVATEL_SDK ${CMAKE_CURRENT_SOURCE_DIR}/novatel_edie)
set(NOVATEL_BIN ${CMAKE_CURRENT_BINARY_DIR}/novatel_edie)
include_directories(
    ${NOVATEL_SDK}/lib
    ${NOVATEL_SDK}/src/decoders/common/api
    ${NOVATEL_SDK}/src/decoders/novatel/api
    ${NOVATEL_SDK}/src/hw_interface/stream_interface/api
    ${NOVATEL_SDK}/src
    ${NOVATEL_BIN}
)

# Python 모듈 생성
pybind11_add_module(${PROJECT_NAME} imu_converter.cpp)

# 의존성 추가
add_dependencies(${PROJECT_NAME} common novatel stream_interface)

# Python 라이브러리 링크
target_link_libraries(${PROJECT_NAME} PRIVATE
    ${PYTHON_LIBRARIES}
    ${PROJECT_LINK_LIBS}
)

# 타겟의 인클루드 디렉토리 설정
target_include_directories(${PROJECT_NAME} PRIVATE
    ${NOVATEL_SDK}/src/decoders/common/api
    ${NOVATEL_SDK}/src/decoders/novatel/api
    ${NOVATEL_SDK}/src/hw_interface/stream_interface/api
    ${NOVATEL_SDK}/src
    ${NOVATEL_BIN}
)

# 빌드 후 공유 라이브러리를 상위 디렉토리로 복사
add_custom_command(TARGET imu_converter POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
    $<TARGET_FILE:imu_converter>
    ${CMAKE_CURRENT_SOURCE_DIR}
)
