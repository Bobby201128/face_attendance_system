# -*- coding: utf-8 -*-
"""
人脸识别签到系统 - 配置文件
"""
import os

# ==================== 基础路径 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACES_DIR = os.path.join(BASE_DIR, "faces")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATABASE_PATH = os.path.join(DATA_DIR, "attendance.db")
LOG_FILE = os.path.join(DATA_DIR, "system.log")

# 确保目录存在
os.makedirs(FACES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

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
