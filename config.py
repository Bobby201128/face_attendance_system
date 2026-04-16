# -*- coding: utf-8 -*-
"""
人脸识别签到系统 - 配置文件
"""
import os
import sys

# ==================== 基础路径 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 打包环境：资源在 _MEIPASS，运行时数据在 EXE 同级目录
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = sys._MEIPASS
    RUNTIME_DIR = os.path.dirname(sys.executable)
else:
    RESOURCE_DIR = BASE_DIR
    RUNTIME_DIR = BASE_DIR

# 所有运行时文件统一存放目录
CACHE_DIR = r"C:\face_attendance_system_TEMP"
FACES_DIR = os.path.join(CACHE_DIR, "faces")
DATA_DIR = os.path.join(CACHE_DIR, "data")
MODEL_DIR = os.path.join(CACHE_DIR, "models")
DATABASE_PATH = os.path.join(DATA_DIR, "attendance.db")
LOG_FILE = os.path.join(CACHE_DIR, "system.log")

# 确保目录存在
os.makedirs(FACES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# ==================== 人脸识别参数 ====================
# 识别模式: "fast"(少量人脸快速), "balanced"(均衡), "accurate"(大量人脸高精度)
RECOGNITION_MODE = "balanced"

# 识别阈值 (0.0-1.0, 越高越严格，对于亚洲人脸建议提高到 0.55 - 0.60 范围，避免误识)
RECOGNITION_THRESHOLD = 0.55

# 检测参数
DETECTION_CONFIDENCE = 0.5
TRACKING_CONFIDENCE = 0.5

# 连续识别确认帧数 (连续N帧识别到同一人才确认签到，2-5为推荐范围)
CONFIRM_FRAMES = 3

# 同一人签到冷却时间 (秒)
SIGN_COOLDOWN = 60

# ==================== 摄像头参数 ====================
CAMERA_INDEX = 0
CAMERA_WIDTH = 800
CAMERA_HEIGHT = 600
CAMERA_FPS = 20

# ==================== 签到规则 ====================
# 工作时间段 (24小时制)
WORK_START_HOUR = 9
WORK_START_MINUTE = 0
WORK_END_HOUR = 18
WORK_END_MINUTE = 0

# 迟到宽限时间 (分钟)
LATE_GRACE_MINUTES = 15

# ==================== 网络服务 ====================
# Flask API 服务
API_HOST = "0.0.0.0"
API_PORT = 5000

# 允许跨域
CORS_ORIGINS = "*"

# ==================== UI 参数 ====================
# PC端窗口
WINDOW_TITLE = "人脸识别签到系统"
WINDOW_FULLSCREEN = True

# 签到成功提示显示时间 (毫秒)
SUCCESS_DISPLAY_TIME = 3000

# 签到面板最近记录显示数量
RECENT_RECORDS_COUNT = 10

# ==================== 数据导出 ====================
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

# ==================== 日志 ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# ==================== 网络工具 ====================

def get_network_name():
    """获取当前网络名称（WiFi SSID 或有线网络连接名）"""
    import subprocess
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith('SSID') and ':' in line and 'BSSID' not in line:
                name = line.split(':', 1)[1].strip()
                if name:
                    return name
    except Exception:
        pass

    # 尝试获取有线网络名称
    try:
        result = subprocess.run(
            ['netsh', 'interface', 'show', 'interface'],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.split('\n'):
            line = line.strip()
            if 'Connected' in line or '已连接' in line:
                parts = line.split()
                if parts:
                    return parts[0]
    except Exception:
        pass

    return "未知网络"


def get_local_ip():
    """获取本机局域网IP"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
