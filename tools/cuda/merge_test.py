import time

import numpy as np
import open3d as o3d
import cuda_transform

class E_DIR:
    FRONT = 0
    REAR = 1
    LEFT = 2
    RIGHT = 3

    BFRONT = 4
    BREAR = 5
    BLEFT = 6
    BRIGHT = 7

# 보정 행렬 (북: 0, 남: 1, 동: 2, 서: 3)
calibration_matrices = {
    E_DIR.FRONT: np.array([
        [-0.0091602, -0.99991858, -0.00337806, -0.0171],
        [0.9960417, -0.00942186, 0.08800358, 1.7897],
        [-0.0880313, -0.0025557, 0.9961143, 1.2491],
        [0., 0., 0., 1.]
    ], dtype=np.float32).flatten(),
    E_DIR.REAR: np.array([
        [-0.0069236, -1.00004508, -0.00971184, -0.0171],
        [-0.98944668, 0.0052067, 0.14559456, -0.4718],
        [-0.14553264, 0.01059936, -0.98952874, 1.1429],
        [0., 0., 0., 1.]
    ], dtype=np.float32).flatten(),
    E_DIR.LEFT: np.array([
        [-0.98537876, 0.01206198, -0.17048562, -0.5694],
        [-0.01503738, -0.99984788, 0.01617282, 1.4914],
        [-0.17024898, 0.01849842, 0.98522812, 1.2638],
        [0., 0., 0., 1.]
    ], dtype=np.float32).flatten(),
    E_DIR.RIGHT: np.array([
        [0.9856652, -0.00595396, 0.16860688, 0.5494],
        [0.00679996, 0.99996702, -0.00444056, 1.5256],
        [-0.16857488, 0.00552344, 0.98567318, 1.2638],
        [0., 0., 0., 1.]
    ], dtype=np.float32).flatten(),

    E_DIR.BFRONT: np.array([
        [-0.0091602, -0.99991858, -0.00337806, -0.0171],
        [0.9960417, -0.00942186, 0.08800358, 1.7897],
        [-0.0880313, -0.0025557, 0.9961143, 1.2491],
        [0., 0., 0., 1.]
    ], dtype=np.float32).flatten(),
    E_DIR.BREAR: np.array([
        [-0.0069236, -1.00004508, -0.00971184, -0.0171],
        [-0.98944668, 0.0052067, 0.14559456, -0.4718],
        [-0.14553264, 0.01059936, -0.98952874, 1.1429],
        [0., 0., 0., 1.]
    ], dtype=np.float32).flatten(),
    E_DIR.BLEFT: np.array([
        [-0.98537876, 0.01206198, -0.17048562, -0.5694],
        [-0.01503738, -0.99984788, 0.01617282, 1.4914],
        [-0.17024898, 0.01849842, 0.98522812, 1.2638],
        [0., 0., 0., 1.]
    ], dtype=np.float32).flatten(),
    E_DIR.BRIGHT: np.array([
        [0.9856652, -0.00595396, 0.16860688, 0.5494],
        [0.00679996, 0.99996702, -0.00444056, 1.5256],
        [-0.16857488, 0.00552344, 0.98567318, 1.2638],
        [0., 0., 0., 1.]
    ], dtype=np.float32).flatten(),

}

def merge_points_with_calibration_cuda(pcd_file_paths, calibration_matrices):
    """각 변환을 CUDA 기반으로 수행하여 병합"""
    merged_points = []

    for idx, pcd_file_path in enumerate(pcd_file_paths):
        # PCD 파일 읽기
        pcd = o3d.io.read_point_cloud(pcd_file_path)
        points = np.asarray(pcd.points).astype(np.float32)

        # 해당 PCD 파일의 변환 행렬 가져오기
        calibration_matrix = calibration_matrices[idx]

        # CUDA 기반 변환 수행
        # print("aaa")
        transformed_points = cuda_transform.cuda_transform(points, calibration_matrix)
        # print("bbb")

        # 변환된 점 추가
        merged_points.append(transformed_points)

    # 모든 변환된 점 병합
    return np.vstack(merged_points)

def save_pcd(points, filename):
    """점 데이터를 PCD 파일로 저장"""
    print("Points dtype before conversion:", points.dtype)

    # 배열 타입 변환 (float32 → float64)
    points = points.astype(np.float64)

    print("Points dtype after conversion:", points.dtype)
    print("Points shape:", points.shape)

    # PointCloud 생성 및 저장
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    o3d.io.write_point_cloud(filename, pcd)
    print(f"PCD 파일 저장 완료: {filename}")


def main():


    while True:

        # pcd_file_paths = [
        #     "/home/oracle/project/project_swm/pyTest/pybindTest/res/src/at128_front.pcd",
        #     "/home/oracle/project/project_swm/pyTest/pybindTest/res/src/at128_rear.pcd",
        #     "/home/oracle/project/project_swm/pyTest/pybindTest/res/src/at128_left.pcd",
        #     "/home/oracle/project/project_swm/pyTest/pybindTest/res/src/at128_right.pcd",
        #
        #     "/home/oracle/project/project_swm/pyTest/pybindTest/res/src/rsbp_front.pcd",
        #     "/home/oracle/project/project_swm/pyTest/pybindTest/res/src/rsbp_rear.pcd",
        #     "/home/oracle/project/project_swm/pyTest/pybindTest/res/src/rsbp_left.pcd",
        #     "/home/oracle/project/project_swm/pyTest/pybindTest/res/src/rsbp_right.pcd",
        # ]

        pcd_file_paths = [
            "./res/at128_front.pcd",
            "./res/at128_rear.pcd",
            "./res/at128_left.pcd",
            "./res/at128_right.pcd",

            "./res/rsbp_front.pcd",
            "./res/rsbp_rear.pcd",
            "./res/rsbp_left.pcd",
            "./res/rsbp_right.pcd",
        ]

        # 데이터 병합 (CUDA 기반 변환 수행)
        merged_points = merge_points_with_calibration_cuda(pcd_file_paths, calibration_matrices)

        # 병합된 데이터 저장
        output_pcd_file = "./res/merged_cuda_110.pcd"
        save_pcd(merged_points, output_pcd_file)

        time.sleep(0)
        return

if __name__ == '__main__':
    main()



