# -*- coding: utf-8 -*-
"""
诊断 face_recognition 库的图像格式问题
"""
import cv2
import numpy as np
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_face_recognition_formats():
    """测试不同的图像格式"""
    print("测试 face_recognition 库的图像格式要求...")

    try:
        import face_recognition
        print("face_recognition 库已加载")
    except ImportError:
        print("face_recognition 库未安装，跳过测试")
        return

    # 打开摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("无法打开摄像头")
        return

    ret, frame = cap.read()
    if not ret:
        print("无法读取帧")
        cap.release()
        return

    print(f"原始帧 - shape: {frame.shape}, dtype: {frame.dtype}")

    # 测试不同的图像格式
    test_cases = [
        ("直接BGR", frame.copy()),
        ("BGR->RGB", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)),
        ("BGR->RGB->contiguous", np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))),
        ("BGR->RGB->copy", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy()),
    ]

    # 添加缩小版本
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)

    test_cases.extend([
        ("缩小RGB", small_frame),
        ("缩小RGB->contiguous", np.ascontiguousarray(small_frame)),
        ("缩小RGB->copy", small_frame.copy()),
        ("强制新数组", np.array(small_frame, dtype=np.uint8)),
        ("强制新连续数组", np.ascontiguousarray(np.array(small_frame, dtype=np.uint8))),
    ])

    for name, test_image in test_cases:
        print(f"\n测试: {name}")
        print(f"  shape: {test_image.shape}, dtype: {test_image.dtype}, "
              f"C_CONTIGUOUS: {test_image.flags['C_CONTIGUOUS']}, "
              f"min: {test_image.min()}, max: {test_image.max()}")

        try:
            # 尝试调用 face_locations
            locations = face_recognition.face_locations(test_image, model="hog")
            print(f"  ✓ 成功! 检测到 {len(locations)} 个人脸")
            break  # 如果成功就不继续测试了
        except Exception as e:
            print(f"  ✗ 失败: {e}")

    cap.release()

if __name__ == '__main__':
    print("=" * 60)
    print("face_recognition 图像格式诊断")
    print("=" * 60)
    test_face_recognition_formats()
    print("=" * 60)
