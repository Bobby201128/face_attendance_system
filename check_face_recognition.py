# -*- coding: utf-8 -*-
"""
检查 face_recognition 库状态
"""
import sys

def check_face_recognition():
    """检查 face_recognition 库"""
    print("=" * 70)
    print("face_recognition 库状态检查")
    print("=" * 70)

    # 1. 检查模块是否可以导入
    print("\n1. 检查模块导入...")
    try:
        import face_recognition
        print("   ✓ face_recognition 可以导入")

        # 2. 检查版本
        if hasattr(face_recognition, '__version__'):
            print(f"   版本: {face_recognition.__version__}")
        else:
            print("   版本: Unknown")

        # 3. 检查依赖
        print("\n2. 检查依赖库...")
        try:
            import dlib
            print(f"   ✓ dlib 已安装")
            if hasattr(dlib, '__version__'):
                print(f"   版本: {dlib.__version__}")
        except ImportError:
            print("   ✗ dlib 未安装")

        # 4. 简单测试
        print("\n3. 功能测试...")
        try:
            import numpy as np
            import cv2

            # 创建一个简单的测试图像
            test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            print(f"   创建测试图像: {test_image.shape}, {test_image.dtype}")

            # 测试 face_locations
            print("   测试 face_locations...")
            locations = face_recognition.face_locations(test_image, model="hog")
            print(f"   ✓ face_locations 正常 (检测到 {len(locations)} 个人脸)")

            return True

        except Exception as e:
            print(f"   ✗ 功能测试失败: {e}")
            return False

    except ImportError as e:
        print(f"   ✗ face_recognition 未安装: {e}")
        print("\n" + "=" * 70)
        print("安装指南:")
        print("=" * 70)
        print("\n推荐方法 - 使用 conda:")
        print("  1. 下载并安装 Miniconda: https://docs.conda.io/en/latest/miniconda.html")
        print("  2. 打开 Anaconda Prompt")
        print("  3. 运行:")
        print("     conda install -c conda-forge dlib")
        print("     pip install face-recognition")
        print("\n替代方法 - 使用预编译包:")
        print("  1. 安装 Visual Studio Build Tools")
        print("  2. 下载预编译的 dlib wheel")
        print("  3. pip install dlib-xxx.whl")
        print("  4. pip install face-recognition")
        print("=" * 70)
        return False

    except Exception as e:
        print(f"   ✗ 检查过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        success = check_face_recognition()

        print("\n" + "=" * 70)
        if success:
            print("状态: ✓ face_recognition 库正常")
            print("\n可以运行完整系统:")
            print("  python main.py")
        else:
            print("状态: ✗ face_recognition 库有问题")
            print("\n请按照上面的指南安装 face_recognition")
        print("=" * 70)

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n检查过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
