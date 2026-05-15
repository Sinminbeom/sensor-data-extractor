#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <cuda_runtime.h>
#include <iostream>

namespace py = pybind11;

// CUDA 커널
__global__ void transform_points(float* points, float* matrix, float* output, int num_points) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < num_points) {
        float x = points[idx * 3];
        float y = points[idx * 3 + 1];
        float z = points[idx * 3 + 2];

        // 변환 행렬 적용
        output[idx * 3 + 0] = matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3];
        output[idx * 3 + 1] = matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7];
        output[idx * 3 + 2] = matrix[8] * x + matrix[9] * y + matrix[10] * z + matrix[11];
    }
}

// C++에서 호출할 함수
py::array_t<float> cuda_transform(py::array_t<float> input_points, py::array_t<float> matrix) {
    // NumPy 배열 -> C++ 배열로 변환
    py::buffer_info points_info = input_points.request();
    py::buffer_info matrix_info = matrix.request();

    int num_points = points_info.shape[0];
    float* points = static_cast<float*>(points_info.ptr);
    float* transform_matrix = static_cast<float*>(matrix_info.ptr);

    // CUDA 메모리 할당
    float *d_points, *d_matrix, *d_output;
    cudaMalloc(&d_points, num_points * 3 * sizeof(float));
    cudaMalloc(&d_matrix, 16 * sizeof(float));
    cudaMalloc(&d_output, num_points * 3 * sizeof(float));

    // CUDA 메모리 복사
    cudaMemcpy(d_points, points, num_points * 3 * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(d_matrix, transform_matrix, 16 * sizeof(float), cudaMemcpyHostToDevice);

    // CUDA 커널 실행
    int threads = 256;
    int blocks = (num_points + threads - 1) / threads;
    transform_points<<<blocks, threads>>>(d_points, d_matrix, d_output, num_points);

    // 결과를 Python으로 복사
    auto result = py::array_t<float>({num_points, 3});
    py::buffer_info result_info = result.request();
    cudaMemcpy(result_info.ptr, d_output, num_points * 3 * sizeof(float), cudaMemcpyDeviceToHost);

    // CUDA 메모리 해제
    cudaFree(d_points);
    cudaFree(d_matrix);
    cudaFree(d_output);

    return result;
}

// pybind11 모듈 정의
PYBIND11_MODULE(cuda_transform, m) {
    m.def("cuda_transform", &cuda_transform, "CUDA 기반 포인트 변환");
}
