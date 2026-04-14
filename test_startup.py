# -*- coding: utf-8 -*-
"""
快速启动测试脚本 - 验证系统是否可以正常启动
"""
import sys
import io

# 设置UTF-8编码输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def test_imports():
    """测试关键模块导入"""
    print("=" * 60)
    print("测试模块导入")
    print("=" * 60)

    try:
        print("1. 导入database.py...")
        from database import db
        print("[OK] database模块导入成功")

        print("2. 导入config.py...")
        import config
        print("[OK] config模块导入成功")

        print("3. 导入pc_app.py...")
        from pc_app import MainWindow
        print("[OK] pc_app模块导入成功")

        print("4. 导入pc_app_extensions.py...")
        from pc_app_extensions import EnvironmentDialog
        print("[OK] pc_app_extensions模块导入成功")

        print("5. 导入api_server.py...")
        from api_server import app
        print("[OK] api_server模块导入成功")

        return True

    except Exception as e:
        print(f"[ERROR] 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database():
    """测试数据库连接"""
    print("\n" + "=" * 60)
    print("测试数据库连接")
    print("=" * 60)

    try:
        from database import db

        # 测试查询
        environments = db.get_all_environments()
        print(f"[OK] 数据库连接正常")
        print(f"[INFO] 环境数量: {len(environments)}")

        categories = db.get_all_categories()
        print(f"[INFO] 分类数量: {len(categories)}")

        return True

    except Exception as e:
        print(f"[ERROR] 数据库测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n")
    print("╔══════════════════════════════════════════════╗")
    print("║      人脸识别签到系统 - 启动测试             ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # 测试模块导入
    if not test_imports():
        print("\n[FAIL] 模块导入测试失败，请检查错误信息")
        return False

    # 测试数据库
    if not test_database():
        print("\n[FAIL] 数据库测试失败，请检查数据库配置")
        return False

    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    print("[OK] 所有测试通过！系统可以正常启动")
    print()
    print("启动命令:")
    print("  python main.py")
    print()
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] 测试过程发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
