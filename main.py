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


# ==================== 模型下载 ====================
MODEL_API_URL = "https://www.123865.com/b/api/v2/share/download/info?1491576389=1776352901-6548828-3045685372"

MODEL_TASKS = [
    {
        "name": "shape_predictor_68_face_landmarks.dat",
        "display": "人脸关键点模型 (68点)",
        "payload": {"ShareKey": "PZhQvd-yHE4H", "FileID": 27177982,
                    "S3keyFlag": "1693978-0", "Size": 64040097,
                    "Etag": "677a91476056de0507f1915adc7ef86a"},
    },
    {
        "name": "dlib_face_recognition_resnet_model_v1.dat",
        "display": "人脸特征向量模型",
        "payload": {"ShareKey": "PZhQvd-VHE4H", "FileID": 27177981,
                    "S3keyFlag": "1693978-0", "Size": 21428389,
                    "Etag": "1b31cc4419cc8f1018117249b64bd683"},
    },
]

MODEL_DIR = r"C:\face_attendance_system_TEMP\models"


def _check_model(name):
    """检查模型文件是否存在"""
    # exe 模式：从 _MEIPASS 中查找
    if getattr(sys, 'frozen', False):
        try:
            model_path = os.path.join(sys._MEIPASS, 'face_recognition_models', 'models', name)
            return os.path.exists(model_path)
        except Exception:
            return False
    # py 模式：先查包目录，再查 TEMP
    try:
        import face_recognition_models
        if name == "shape_predictor_68_face_landmarks.dat":
            pkg_path = face_recognition_models.pose_predictor_model_location()
        else:
            pkg_path = face_recognition_models.face_recognition_model_location()
        if os.path.exists(pkg_path):
            return True
    except Exception:
        pass
    return os.path.exists(os.path.join(MODEL_DIR, name))


def _get_download_url(payload, callback=None):
    """向 API 发送 POST 请求获取下载链接"""
    import urllib.request, json
    data = json.dumps(payload).encode()
    req = urllib.request.Request(MODEL_API_URL, data=data,
                                headers={"Content-Type": "application/json",
                                         "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    url = result.get("data", {}).get("downloadPath", "")
    if url and not url.startswith("http"):
        url = "https://" + url.lstrip("/")
    if callback:
        callback("链接获取成功")
    return url


def _download_file(url, filepath, callback=None):
    """下载文件，callback(downloaded_bytes, total_bytes)"""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        total = int(resp.headers.get('Content-Length', 0))
        downloaded = 0
        with open(filepath, 'wb') as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if callback:
                    callback(downloaded, total)


def _patch_model_paths():
    """确保模型路径指向实际存在的模型文件"""
    if getattr(sys, 'frozen', False):
        # exe 模式：强制指向 _MEIPASS 中打包的模型
        try:
            import face_recognition_models
            models_dir = os.path.join(sys._MEIPASS, 'face_recognition_models', 'models')
            face_recognition_models.pose_predictor_model_location = lambda: os.path.join(
                models_dir, "shape_predictor_68_face_landmarks.dat")
            face_recognition_models.face_recognition_model_location = lambda: os.path.join(
                models_dir, "dlib_face_recognition_resnet_model_v1.dat")
        except Exception:
            pass
        return
    # py 模式
    try:
        import face_recognition_models
        # 检查包目录是否已有模型
        for func in [face_recognition_models.pose_predictor_model_location,
                     face_recognition_models.face_recognition_model_location]:
            if os.path.exists(func()):
                return  # 包里有模型，不需要 patch
        # 包里没有，patch 到 TEMP 目录
        face_recognition_models.pose_predictor_model_location = lambda: os.path.join(
            MODEL_DIR, "shape_predictor_68_face_landmarks.dat")
        face_recognition_models.face_recognition_model_location = lambda: os.path.join(
            MODEL_DIR, "dlib_face_recognition_resnet_model_v1.dat")
    except Exception:
        pass


def install_models(set_status, process_events=None):
    """主线程同步检查并下载模型，通过 process_events 保持 UI 响应"""
    def _pe():
        if process_events:
            process_events()

    set_status("检测模型文件...", 15)
    _pe()
    os.makedirs(MODEL_DIR, exist_ok=True)

    missing = [t for t in MODEL_TASKS if not _check_model(t["name"])]
    if not missing:
        _patch_model_paths()
        set_status("模型文件就绪", 85)
        return True, None

    total_tasks = len(missing)
    total_bytes = sum(t["payload"]["Size"] for t in missing)
    done_bytes = 0

    for i, task in enumerate(missing):
        name = task["name"]
        display = task["display"]
        label = f"[{i+1}/{total_tasks}] {display}"

        set_status(f"{label} - 正在获取链接...", 15)
        _pe()
        try:
            url = _get_download_url(task["payload"])
            if not url:
                return False, f"{display} 获取下载链接失败"
        except Exception as e:
            return False, f"{display} 获取链接失败: {e}"

        filepath = os.path.join(MODEL_DIR, name)
        set_status(f"{label} - 开始下载...", 20)
        _pe()
        try:
            def make_cb(lbl, base):
                def cb(downloaded, file_total):
                    cur = base + downloaded
                    pct = 15 + int(cur * 70 // total_bytes)
                    mb_d = downloaded / (1024 * 1024)
                    mb_t = file_total / (1024 * 1024)
                    set_status(
                        f"{lbl} - {mb_d:.1f}MB / {mb_t:.1f}MB "
                        f"({downloaded*100//file_total if file_total else 0}%)", pct)
                    _pe()
                return cb
            _download_file(url, filepath, make_cb(label, done_bytes))
        except Exception as e:
            return False, f"{display} 下载失败: {e}"

        done_bytes += task["payload"]["Size"]

    _patch_model_paths()
    set_status("模型文件就绪", 85)
    return True, None


# ==================== 启动加载窗口 ====================
class SplashWindow:
    """启动加载窗口"""

    def __init__(self):
        from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                                     QLabel, QProgressBar)
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QColor, QPalette

        # 如果还没有 QApplication 则创建
        self._created_app = False
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
            self._created_app = True

        self.app.setStyle('Fusion')

        # 暗色主题
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
        palette.setColor(QPalette.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.Base, QColor(42, 42, 42))
        palette.setColor(QPalette.Button, QColor(50, 50, 50))
        palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
        palette.setColor(QPalette.Highlight, QColor(76, 175, 80))
        self.app.setPalette(palette)

        self.window = QWidget()
        self.window.setFixedSize(420, 160)
        self.window.setWindowTitle("智脸考勤")
        self.window.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.window.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333;")

        icon_path = os.path.join(config.RESOURCE_DIR, 'icon.png')
        if os.path.exists(icon_path):
            from PyQt5.QtGui import QIcon
            self.window.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self.window)
        layout.setContentsMargins(24, 20, 24, 20)

        self.title_label = QLabel("智脸考勤")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4CAF50; margin-bottom: 10px;")
        layout.addWidget(self.title_label)

        self.status_label = QLabel("正在初始化...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px; color: #aaa;")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #333; border-radius: 3px; }
            QProgressBar::chunk { background-color: #4CAF50; border-radius: 3px; }
        """)
        layout.addWidget(self.progress)

        layout.addSpacing(8)

        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(self.detail_label)

        # 居中显示
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - 420) // 2
        y = (screen.height() - 160) // 2
        self.window.move(x, y)

    def show(self):
        self.window.show()
        self.app.processEvents()

    def update_status(self, text, progress=None, detail=""):
        self.status_label.setText(text)
        if progress is not None:
            self.progress.setValue(progress)
        if detail:
            self.detail_label.setText(detail)
        self.app.processEvents()

    def close(self):
        self.window.close()


# ==================== 日志和工具 ====================
def setup_logging():
    """配置日志"""
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.MODEL_DIR, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format=config.LOG_FORMAT,
        handlers=[
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
    from api_server import app

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
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QPalette, QColor, QIcon
    from PyQt5.QtCore import QTimer
    from pc_app import MainWindow
    from database import db
    from device_discovery import DeviceDiscovery

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

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

    icon_path = os.path.join(config.RESOURCE_DIR, 'icon.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window.face_engine = face_engine
    window.camera = camera_manager
    window._load_faces()

    device_config = db.get_device_config()
    device_name = device_config.get('device_name', '未命名设备')
    device_id = db.ensure_device_id()

    device_discovery = DeviceDiscovery(device_name, device_id, config.API_PORT)
    device_discovery.start_broadcast()
    window.device_discovery = device_discovery

    window.show()
    sys.exit(app.exec_())


# ==================== 主入口 ====================
def main():
    """主入口"""
    from PyQt5.QtWidgets import QDialog

    # 创建加载窗口
    splash = SplashWindow()
    splash.show()
    splash.update_status("正在初始化...", 5, "")

    logger = setup_logging()
    logger.info("系统启动中")

    # 检查并下载模型（主线程同步，processEvents 保持 UI 响应）
    splash.update_status("检测模型文件...", 15)
    ok, err = install_models(
        lambda msg, pct=None: splash.update_status(msg, pct if pct is not None else 15, ""),
        process_events=lambda: splash.app.processEvents()
    )
    if not ok:
        splash.update_status(f"模型下载失败: {err}", 100, err)
        time.sleep(5)
        splash.close()
        return

    # 初始化数据库
    splash.update_status("初始化数据库...", 88)
    from database import db
    logger.info("数据库初始化完成")

    # 初始化人脸识别引擎
    splash.update_status("加载人脸识别引擎...", 92)
    from face_engine import FaceEngine, CameraManager
    face_engine = FaceEngine()
    camera_manager = CameraManager(config.CAMERA_INDEX)
    logger.info("人脸识别引擎初始化完成")

    # 加载已注册人脸
    splash.update_status("加载已注册人脸...", 96)
    persons = db.get_persons_with_encoding()
    face_engine.load_known_faces(persons)
    logger.info(f"已加载 {len(persons)} 个人脸编码")

    # 确保设备ID存在
    db.ensure_device_id()

    # 检查设备名称
    splash.update_status("初始化设备...", 80)
    device_config = db.get_device_config()
    device_name = device_config.get('device_name', '').strip()

    if not device_name:
        from device_name_dialog import DeviceNameDialog
        dialog = DeviceNameDialog()
        splash.close()
        if dialog.exec_() == QDialog.Accepted:
            device_name = dialog.get_device_name()
            db.update_device_config(device_name=device_name)
            logger.info(f"设备已命名: {device_name}")
        else:
            return
        splash.show()

    # 启动API服务
    splash.update_status("启动API服务...", 90)
    start_api_server_thread(face_engine, camera_manager)
    time.sleep(1)

    local_ip = get_local_ip()
    logger.info(f"本机IP: {local_ip}")
    logger.info(f"手机端访问: http://{local_ip}:{config.API_PORT}")

    splash.update_status("启动完成", 100, f"手机端: http://{local_ip}:{config.API_PORT}")
    time.sleep(0.5)
    splash.close()

    # 启动PC端应用
    start_pc_app(face_engine, camera_manager)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"系统启动失败: {e}", exc_info=True)
