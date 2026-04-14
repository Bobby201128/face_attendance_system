# -*- coding: utf-8 -*-
"""
人脸识别签到系统 - 主入口
同时启动 PyQt5 PC端应用 和 Flask API 服务
"""
import os
import sys
import logging
import threading
import time
import socket

import config

# 确保项目目录在路径中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def setup_logging():
    """配置日志"""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format=config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.LOG_FILE, encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)


def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def start_api_server_thread(face_engine=None, camera_manager=None):
    """在后台线程中启动Flask API服务"""
    from api_server import app, start_api_server

    # 保存引用供API使用
    if face_engine:
        app._face_engine = face_engine
    if camera_manager:
        app._camera_manager = camera_manager

    from datetime import datetime
    app._start_time = datetime.now()
    app._camera_running = False
    app._camera_snapshot = None
    app._face_count = 0
    app._recognition_mode = config.RECOGNITION_MODE

    def run():
        import logging
        thread_logger = logging.getLogger(__name__)
        thread_logger.info(f"API服务启动中... http://{config.API_HOST}:{config.API_PORT}")
        app.run(
            host=config.API_HOST,
            port=config.API_PORT,
            debug=False,
            threaded=True,
            use_reloader=False
        )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def start_pc_app(face_engine, camera_manager):
    """启动PC端PyQt5应用"""
    from PyQt5.QtWidgets import QApplication, QDialog
    from PyQt5.QtGui import QPalette, QColor
    from pc_app import MainWindow
    from pc_app_extensions import EnvironmentDialog

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 暗色主题（黑灰白）
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(26, 26, 26))
    palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.Base, QColor(42, 42, 42))
    palette.setColor(QPalette.AlternateBase, QColor(26, 26, 26))
    palette.setColor(QPalette.ToolTipBase, QColor(224, 224, 224))
    palette.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
    palette.setColor(QPalette.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.Button, QColor(42, 42, 42))
    palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
    palette.setColor(QPalette.Highlight, QColor(64, 64, 64))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = MainWindow()

    # 共享引擎和摄像头
    window.face_engine = face_engine
    window.camera = camera_manager
    window._load_faces()

    # 显示环境选择对话框
    try:
        from database import db
        environments = db.get_all_environments(include_inactive=False)

        if len(environments) > 1:
            # 有多个环境时，显示选择对话框
            dialog = EnvironmentDialog(window)
            result = dialog.exec_()
            if result == QDialog.Accepted:
                selected_env = dialog.get_selected_environment()
                if selected_env:
                    window._apply_environment_settings(selected_env)
        elif len(environments) == 1:
            # 只有一个环境，自动应用
            window._apply_environment_settings(environments[0])
    except Exception as e:
        logger.warning(f"环境选择失败，使用默认设置: {e}")

    window.show()

    sys.exit(app.exec_())


def main():
    """主入口"""
    logger = setup_logging()

    print("""
    ╔══════════════════════════════════════════════╗
    ║         人脸识别签到系统 v1.0                ║
    ║                                            ║
    ║  PC端: PyQt5 全屏签到界面                    ║
    ║  移动端: Web 管理界面                        ║
    ╚══════════════════════════════════════════════╝
    """)

    # 初始化数据库
    from database import db
    logger.info("数据库初始化完成")

    # 初始化人脸识别引擎
    from face_engine import FaceEngine, CameraManager
    face_engine = FaceEngine()
    camera_manager = CameraManager(config.CAMERA_INDEX)
    logger.info("人脸识别引擎初始化完成")

    # 加载已注册人脸
    persons = db.get_persons_with_encoding()
    face_engine.load_known_faces(persons)
    logger.info(f"已加载 {len(persons)} 个人脸编码")

    # 启动API服务 (后台线程)
    api_thread = start_api_server_thread(face_engine, camera_manager)
    time.sleep(1)  # 等待API服务启动

    local_ip = get_local_ip()
    logger.info(f"本机IP: {local_ip}")
    logger.info(f"手机端访问: http://{local_ip}:{config.API_PORT}")
    print(f"\n  手机端请访问: http://{local_ip}:{config.API_PORT}")
    print(f"  默认密码: admin123")
    print(f"  按 Ctrl+C 退出\n")

    # 启动PC端应用 (主线程)
    start_pc_app(face_engine, camera_manager)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n系统已退出")
    except Exception as e:
        logging.error(f"系统启动失败: {e}", exc_info=True)
        print(f"\n启动失败: {e}")
        print("请检查依赖是否安装: pip install -r requirements.txt")
        input("按回车退出...")
