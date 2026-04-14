# -*- coding: utf-8 -*-
"""
人脸识别签到系统 - PC端全屏应用 (PyQt5)
功能: 摄像头大画面显示、实时人脸识别、签到记录、数据统计、系统设置
"""
import os
import sys
import json
import time
import logging
import threading
import pickle
from datetime import datetime, date, timedelta

import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QStackedWidget, QGroupBox, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QTimeEdit, QCheckBox, QTextEdit,
    QScrollArea, QSplitter, QFrame, QSystemTrayIcon, QMenu, QAction,
    QDialog, QFileDialog, QMessageBox, QProgressBar, QTabWidget,
    QGridLayout, QSizePolicy, QAbstractItemView
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QDate, QTime
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor, QIcon, QPalette

import config
from database import db
from face_engine import FaceEngine, CameraManager
from video_threads import VideoThread, RecognitionThread

logger = logging.getLogger(__name__)


# ==================== 样式表 ====================

DARK_STYLE = """
QMainWindow {
    background-color: #1a1a2e;
}
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
}
QLabel {
    color: #e0e0e0;
    font-size: 14px;
}
QLabel#titleLabel {
    font-size: 24px;
    font-weight: bold;
    color: #00d4ff;
}
QLabel#statValue {
    font-size: 36px;
    font-weight: bold;
    color: #00d4ff;
}
QLabel#statLabel {
    font-size: 13px;
    color: #a0a0a0;
}
QLabel#timeLabel {
    font-size: 48px;
    font-weight: bold;
    color: #00d4ff;
}
QLabel#dateLabel {
    font-size: 18px;
    color: #a0a0a0;
}
QLabel#signName {
    font-size: 28px;
    font-weight: bold;
    color: #00ff88;
}
QLabel#signInfo {
    font-size: 16px;
    color: #a0a0a0;
}
QPushButton {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 14px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #0f3460;
    border-color: #00d4ff;
}
QPushButton:pressed {
    background-color: #00d4ff;
    color: #1a1a2e;
}
QPushButton#primaryBtn {
    background-color: #0f3460;
    border-color: #00d4ff;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #00d4ff;
    color: #1a1a2e;
}
QPushButton#dangerBtn {
    background-color: #3a0a0a;
    border-color: #ff4444;
}
QPushButton#dangerBtn:hover {
    background-color: #ff4444;
    color: white;
}
QPushButton#successBtn {
    background-color: #0a3a0a;
    border-color: #00ff88;
}
QPushButton#successBtn:hover {
    background-color: #00ff88;
    color: #1a1a2e;
}
QGroupBox {
    border: 1px solid #0f3460;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    font-size: 15px;
    color: #00d4ff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}
QTableWidget {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 6px;
    gridline-color: #0f3460;
    font-size: 13px;
}
QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #0f3460;
}
QTableWidget::item:selected {
    background-color: #0f3460;
}
QHeaderView::section {
    background-color: #0f3460;
    color: #00d4ff;
    padding: 8px;
    border: none;
    font-weight: bold;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #0f3460;
    border-radius: 6px;
    background-color: #1a1a2e;
}
QTabBar::tab {
    background-color: #16213e;
    color: #a0a0a0;
    padding: 10px 20px;
    border: 1px solid #0f3460;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 14px;
}
QTabBar::tab:selected {
    background-color: #0f3460;
    color: #00d4ff;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QComboBox, QTextEdit {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 4px;
    padding: 6px 10px;
    color: #e0e0e0;
    font-size: 13px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTimeEdit:focus, QComboBox:focus {
    border-color: #00d4ff;
}
QComboBox::drop-down {
    border: none;
    background-color: #16213e;
}
QComboBox QAbstractItemView {
    background-color: #16213e;
    color: #e0e0e0;
    selection-background-color: #0f3460;
}
QScrollArea {
    border: none;
}
QScrollBar:vertical {
    background-color: #1a1a2e;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #0f3460;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QProgressBar {
    border: 1px solid #0f3460;
    border-radius: 4px;
    text-align: center;
    background-color: #16213e;
    color: #00d4ff;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #00d4ff;
    border-radius: 3px;
}
QCheckBox {
    font-size: 13px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #0f3460;
    border-radius: 4px;
    background-color: #16213e;
}
QCheckBox::indicator:checked {
    background-color: #00d4ff;
    border-color: #00d4ff;
}
"""


# ==================== 视频线程已移至 video_threads.py ====================

# VideoThread 和 RecognitionThread 现在从 video_threads 导入


# ==================== 签到成功动画 ====================

class SignSuccessOverlay(QWidget):
    """签到成功覆盖层"""
    hide_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self._fade_out)
        self.opacity = 0
        self.name = ""
        self.info = ""
        self.is_sign_in = True

    def show_sign(self, name, info, is_sign_in=True):
        self.name = name
        self.info = info
        self.is_sign_in = is_sign_in
        self.opacity = 255
        self.hide_timer.start(30)
        self.show()
        self.update()

    def _fade_out(self):
        self.opacity -= 5
        if self.opacity <= 0:
            self.hide_timer.stop()
            self.hide()
            self.hide_signal.emit()
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor, QFont
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 半透明背景
        bg_color = QColor(0, 200, 100, int(self.opacity * 0.7)) if self.is_sign_in else QColor(255, 165, 0, int(self.opacity * 0.7))
        painter.fillRect(self.rect(), bg_color)

        # 文字
        text_color = QColor(255, 255, 255, self.opacity)
        painter.setPen(text_color)

        font = QFont("Microsoft YaHei", 32, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, f"{self.name}\n{self.info}")


# ==================== 主窗口 ====================

class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        # 核心组件（稍后由main.py注入正确的实例）
        self.face_engine = None  # 延迟初始化，避免创建空实例
        self.camera = None
        self.video_thread = None
        self.recognition_thread = None

        # 状态
        self.is_running = False
        self.sign_mode = "auto"  # auto / manual
        self.current_sign_type = "in"  # in / out
        self.last_signed_id = None
        self.last_signed_time = 0
        
        # 最新识别结果（由识别线程更新，显示线程读取）
        self.latest_results = []
        self.results_lock = threading.Lock()

        # 初始化UI
        self._init_ui()
        # 注意：_load_faces() 将在 start_pc_app 中调用

        # 定时器
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._refresh_stats)
        self.stats_timer.start(5000)

        self.records_timer = QTimer()
        self.records_timer.timeout.connect(self._refresh_records)
        self.records_timer.start(3000)

        # 初始刷新
        self._update_clock()
        self._refresh_stats()
        self._refresh_records()

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle(config.WINDOW_TITLE)
        self.setStyleSheet(DARK_STYLE)

        if config.WINDOW_FULLSCREEN:
            self.showFullScreen()

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ===== 左侧: 摄像头区域 =====
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 顶部信息栏
        top_bar = QHBoxLayout()

        self.time_label = QLabel("00:00:00")
        self.time_label.setObjectName("timeLabel")
        top_bar.addWidget(self.time_label)

        top_bar.addStretch()

        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
        top_bar.addWidget(self.date_label)

        left_layout.addLayout(top_bar)

        # 摄像头画面
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("""
            background-color: #0a0a1a;
            border: 2px solid #0f3460;
            border-radius: 10px;
        """)
        self.camera_label.setText("摄像头未启动")
        self.camera_label.setFont(QFont("Microsoft YaHei", 20))
        left_layout.addWidget(self.camera_label, stretch=1)

        # 签到成功提示
        self.sign_success_label = QLabel("")
        self.sign_success_label.setObjectName("signName")
        self.sign_success_label.setAlignment(Qt.AlignCenter)
        self.sign_success_label.setMaximumHeight(60)
        left_layout.addWidget(self.sign_success_label)

        # 底部控制栏
        control_bar = QHBoxLayout()

        self.btn_start = QPushButton("启动摄像头")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setMinimumHeight(45)
        self.btn_start.clicked.connect(self._toggle_camera)
        control_bar.addWidget(self.btn_start)

        self.btn_mode = QPushButton("模式: 自动签到")
        self.btn_mode.setMinimumHeight(45)
        self.btn_mode.clicked.connect(self._toggle_mode)
        control_bar.addWidget(self.btn_mode)

        self.btn_sign_type = QPushButton("签到")
        self.btn_sign_type.setObjectName("successBtn")
        self.btn_sign_type.setMinimumHeight(45)
        self.btn_sign_type.clicked.connect(self._toggle_sign_type)
        self.btn_sign_type.setEnabled(False)
        control_bar.addWidget(self.btn_sign_type)

        self.btn_fullscreen = QPushButton("全屏/退出")
        self.btn_fullscreen.setMinimumHeight(45)
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        control_bar.addWidget(self.btn_fullscreen)

        left_layout.addLayout(control_bar)

        # ===== 右侧: 数据面板 =====
        right_widget = QWidget()
        right_widget.setMaximumWidth(450)
        right_widget.setMinimumWidth(380)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # 标签页
        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)

        # --- 签到统计页 ---
        stats_page = QWidget()
        stats_layout = QVBoxLayout(stats_page)
        stats_layout.setSpacing(8)

        # 统计卡片
        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)

        self.stat_total = self._create_stat_card("总人数", "0")
        self.stat_signed = self._create_stat_card("已签到", "0")
        self.stat_absent = self._create_stat_card("未签到", "0")
        self.stat_late = self._create_stat_card("迟到", "0")

        stats_grid.addWidget(self.stat_total['widget'], 0, 0)
        stats_grid.addWidget(self.stat_signed['widget'], 0, 1)
        stats_grid.addWidget(self.stat_absent['widget'], 1, 0)
        stats_grid.addWidget(self.stat_late['widget'], 1, 1)

        stats_layout.addLayout(stats_grid)

        # 签到率进度条
        rate_group = QGroupBox("签到率")
        rate_layout = QVBoxLayout(rate_group)
        self.rate_bar = QProgressBar()
        self.rate_bar.setRange(0, 100)
        self.rate_bar.setValue(0)
        self.rate_bar.setFormat("%v%")
        self.rate_bar.setMinimumHeight(25)
        rate_layout.addWidget(self.rate_bar)
        stats_layout.addWidget(rate_group)

        # 系统信息
        info_group = QGroupBox("系统信息")
        info_layout = QFormLayout(info_group)
        self.lbl_face_count = QLabel("0")
        self.lbl_mode = QLabel("均衡模式")
        self.lbl_threshold = QLabel(f"{config.RECOGNITION_THRESHOLD:.1%}")
        self.lbl_api_addr = QLabel(f"http://{config.API_HOST}:{config.API_PORT}")
        info_layout.addRow("已注册人脸:", self.lbl_face_count)
        info_layout.addRow("识别模式:", self.lbl_mode)
        info_layout.addRow("识别阈值:", self.lbl_threshold)
        info_layout.addRow("手机访问:", self.lbl_api_addr)
        stats_layout.addWidget(info_group)

        stats_layout.addStretch()
        self.tabs.addTab(stats_page, "统计")

        # --- 签到记录页 ---
        records_page = QWidget()
        records_layout = QVBoxLayout(records_page)

        self.records_table = QTableWidget()
        self.records_table.setColumnCount(5)
        self.records_table.setHorizontalHeaderLabels(["姓名", "工号", "类型", "时间", "状态"])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.records_table.setAlternatingRowColors(True)
        records_layout.addWidget(self.records_table)

        self.tabs.addTab(records_page, "记录")

        # --- 人员管理页 ---
        person_page = QWidget()
        person_layout = QVBoxLayout(person_page)

        # 搜索栏
        search_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索姓名/工号...")
        self.search_input.returnPressed.connect(self._search_persons)
        search_bar.addWidget(self.search_input)

        btn_search = QPushButton("搜索")
        btn_search.clicked.connect(self._search_persons)
        search_bar.addWidget(btn_search)

        btn_add = QPushButton("添加人员")
        btn_add.setObjectName("primaryBtn")
        btn_add.clicked.connect(self._add_person_dialog)
        search_bar.addWidget(btn_add)

        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self._refresh_persons)
        search_bar.addWidget(btn_refresh)

        person_layout.addLayout(search_bar)

        self.person_table = QTableWidget()
        self.person_table.setColumnCount(6)
        self.person_table.setHorizontalHeaderLabels(["姓名", "工号", "部门", "职位", "电话", "状态"])
        self.person_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.person_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.person_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.person_table.setAlternatingRowColors(True)
        self.person_table.cellDoubleClicked.connect(self._edit_person_dialog)
        person_layout.addWidget(self.person_table)

        self.tabs.addTab(person_page, "人员")

        # 添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

        # 签到成功覆盖层
        self.success_overlay = SignSuccessOverlay(self)

    def _create_stat_card(self, label, value):
        """创建统计卡片"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(4)

        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel(label)
        text_label.setObjectName("statLabel")
        text_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(value_label)
        layout.addWidget(text_label)

        return {"widget": widget, "value": value_label}

    # ==================== 摄像头控制 ====================

    def _toggle_camera(self):
        """启动/停止摄像头"""
        if self.is_running:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        """启动摄像头 - 分离式架构"""
        # 检查核心组件是否已初始化
        if self.face_engine is None or self.camera is None:
            QMessageBox.critical(self, "错误", "系统未正确初始化，请重启程序")
            return
            
        face_count = self.face_engine.get_face_count()
        logger.info(f"启动摄像头，当前已注册 {face_count} 个人脸")
        
        if not self.camera.open(width=config.CAMERA_WIDTH, height=config.CAMERA_HEIGHT):
            QMessageBox.critical(self, "错误", "无法打开摄像头，请检查摄像头连接")
            return

        # 启动视频显示线程（只负责流畅显示）
        self.video_thread = VideoThread(self.camera)
        self.video_thread.frame_signal.connect(self._on_video_frame)
        self.video_thread.error_signal.connect(self._on_camera_error)
        self.video_thread.start()

        # 启动识别线程（使用正确的face_engine实例）
        self.recognition_thread = RecognitionThread(self.face_engine)
        self.recognition_thread.result_signal.connect(self._on_recognition_result)
        self.recognition_thread.start()

        self.is_running = True
        self.btn_start.setText("停止摄像头")
        self.btn_start.setObjectName("dangerBtn")
        self.btn_start.setStyleSheet(self.btn_start.styleSheet())
        self.btn_sign_type.setEnabled(True)

        logger.info(f"摄像头已启动（分离式架构），识别线程已绑定到正确的引擎实例")

    def _stop_camera(self):
        """停止摄像头"""
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None

        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread = None

        self.camera.close()
        self.is_running = False
        self.btn_start.setText("启动摄像头")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_sign_type.setEnabled(False)

        self.camera_label.clear()
        self.camera_label.setText("摄像头已停止")
        self.camera_label.setFont(QFont("Microsoft YaHei", 20))

        logger.info("摄像头已停止")

    def _on_video_frame(self, frame):
        """视频帧回调 - 只负责显示和转发给识别线程"""
        if not self.is_running:
            return

        # 复制一份纯净的帧给识别线程，避免绘制边框干扰识别
        clean_frame = frame.copy()

        # 将帧发送给识别线程（非阻塞）
        if self.recognition_thread:
            self.recognition_thread.update_frame(clean_frame)

        # 获取最新识别结果并绘制
        with self.results_lock:
            results = self.latest_results.copy() if self.latest_results else []

        # 在原帧上绘制识别结果以供显示
        if results:
            self.face_engine.draw_results(frame, results)

        # 更新API快照
        try:
            from api_server import app as flask_app
            flask_app._camera_snapshot = frame
            flask_app._camera_running = True
        except:
            pass

        # 显示帧（保持流畅）
        self._display_frame(frame)

    def _on_recognition_result(self, results):
        """识别结果回调 - 由识别线程调用"""
        if not results:
            return
            
        with self.results_lock:
            self.latest_results = results

        # 调试日志：显示识别到的所有人脸
        for result in results:
            name = result.get('name', 'Unknown')
            confidence = result.get('confidence', 0)
            matched = result.get('matched', False)
            
            if name != 'Unknown' and matched:
                logger.debug(f"识别到: {name} (置信度: {confidence:.2%})")
        
        # 检查签到
        for result in results:
            if result.get('confirmed') and not result.get('cooldown'):
                self._handle_sign(result)

    def _display_frame(self, frame):
        """在标签上显示帧（优化版）"""
        # 直接转换并显示，减少中间步骤
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # 缩放适应标签大小，使用快速变换
        label_size = self.camera_label.size()
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            label_size, Qt.KeepAspectRatio, Qt.FastTransformation
        )
        self.camera_label.setPixmap(scaled_pixmap)

    def _on_camera_error(self, msg):
        """摄像头错误处理"""
        logger.error(f"摄像头错误: {msg}")
        self.camera_label.setText(f"摄像头错误: {msg}")

    def _handle_sign(self, result):
        """处理签到"""
        person_id = result['person_id']
        name = result['name']
        confidence = result['confidence']

        # 冷却检查
        now = time.time()
        if person_id == self.last_signed_id and now - self.last_signed_time < config.SIGN_COOLDOWN:
            return

        # 确定签到类型
        sign_type = self.current_sign_type if self.sign_mode == "manual" else self._auto_detect_sign_type(person_id)

        # 保存记录
        record_id = db.add_attendance(
            person_id=person_id,
            sign_type=sign_type,
            confidence=confidence
        )

        self.last_signed_id = person_id
        self.last_signed_time = now

        # 显示签到成功
        sign_text = "签到" if sign_type == "in" else "签退"
        time_str = datetime.now().strftime("%H:%M:%S")

        self.sign_success_label.setText(f"{name} - {sign_text}成功 {time_str}")

        # 判断是否迟到
        is_late = False
        if sign_type == "in":
            settings = db.get_settings()
            work_start = settings.get('work_start', '09:00')
            late_grace = int(settings.get('late_grace', '15'))
            now_time = datetime.now().strftime("%H:%M")
            h, m = map(int, work_start.split(':'))
            late_limit = f"{h}:{m + late_grace:02d}"
            if now_time > late_limit:
                is_late = True

        status_text = f"{sign_text}成功 {time_str}" + (" (迟到)" if is_late else "")

        # 显示覆盖层
        self.success_overlay.show_sign(name, status_text, sign_type == "in")

        # 刷新数据
        self._refresh_stats()
        self._refresh_records()

        logger.info(f"签到: {name} ({sign_text}) 置信度={confidence:.2%}")

    def _auto_detect_sign_type(self, person_id):
        """自动检测签到类型 (根据今日是否已签到)"""
        status = db.get_person_today_status(person_id)
        if status['signed_in'] and not status['signed_out']:
            return 'out'
        return 'in'

    # ==================== 模式控制 ====================

    def _toggle_mode(self):
        """切换签到模式"""
        if self.sign_mode == "auto":
            self.sign_mode = "manual"
            self.btn_mode.setText("模式: 手动签到")
            self.btn_sign_type.setEnabled(self.is_running)
        else:
            self.sign_mode = "auto"
            self.btn_mode.setText("模式: 自动签到")
            self.btn_sign_type.setEnabled(False)

    def _toggle_sign_type(self):
        """切换签到/签退"""
        if self.current_sign_type == "in":
            self.current_sign_type = "out"
            self.btn_sign_type.setText("签退")
            self.btn_sign_type.setObjectName("dangerBtn")
        else:
            self.current_sign_type = "in"
            self.btn_sign_type.setText("签到")
            self.btn_sign_type.setObjectName("successBtn")

    def _toggle_fullscreen(self):
        """切换全屏"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ==================== 数据刷新 ====================

    def _update_clock(self):
        """更新时钟"""
        now = datetime.now()
        self.time_label.setText(now.strftime("%H:%M:%S"))
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        self.date_label.setText(f"{now.strftime('%Y年%m月%d日')} {weekdays[now.weekday()]}")

    def _refresh_stats(self):
        """刷新统计数据"""
        try:
            stats = db.get_today_statistics()
            self.stat_total['value'].setText(str(stats['total_persons']))
            self.stat_signed['value'].setText(str(stats['signed_in']))
            self.stat_absent['value'].setText(str(stats['absent']))
            self.stat_late['value'].setText(str(stats['late_count']))
            self.rate_bar.setValue(int(stats['sign_rate']))

            self.lbl_face_count.setText(str(self.face_engine.get_face_count()))
        except Exception as e:
            logger.error(f"刷新统计失败: {e}")

    def _refresh_records(self):
        """刷新签到记录"""
        try:
            records = db.get_today_attendance()
            self.records_table.setRowCount(len(records))

            settings = db.get_settings()
            work_start = settings.get('work_start', '09:00')
            late_grace = int(settings.get('late_grace', '15'))

            for row, r in enumerate(records):
                sign_type_text = "签到" if r['sign_type'] == 'in' else "签退"
                sign_time = r['sign_time']

                # 判断迟到
                status = "正常"
                if r['sign_type'] == 'in':
                    try:
                        t = datetime.strptime(sign_time, "%Y-%m-%d %H:%M:%S")
                        h, m = map(int, work_start.split(':'))
                        limit = t.replace(hour=h, minute=m + late_grace)
                        if t > limit:
                            status = "迟到"
                    except:
                        pass

                items = [
                    r.get('name', ''),
                    r.get('employee_id', ''),
                    sign_type_text,
                    sign_time.split(' ')[1] if ' ' in sign_time else sign_time,
                    status
                ]

                for col, text in enumerate(items):
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignCenter)
                    if status == "迟到":
                        item.setForeground(QColor(255, 100, 100))
                    self.records_table.setItem(row, col, item)

        except Exception as e:
            logger.error(f"刷新记录失败: {e}")

    def _refresh_persons(self):
        """刷新人员列表"""
        try:
            persons, total = db.get_all_persons(include_inactive=True, per_page=200)
            self.person_table.setRowCount(len(persons))

            for row, p in enumerate(persons):
                items = [
                    p.get('name', ''),
                    p.get('employee_id', ''),
                    p.get('department', ''),
                    p.get('position', ''),
                    p.get('phone', ''),
                    "启用" if p.get('status', 1) == 1 else "禁用"
                ]

                for col, text in enumerate(items):
                    item = QTableWidgetItem(str(text) if text else '')
                    item.setTextAlignment(Qt.AlignCenter)
                    if col == 5 and text == "禁用":
                        item.setForeground(QColor(255, 100, 100))
                    self.person_table.setItem(row, col, item)

        except Exception as e:
            logger.error(f"刷新人员列表失败: {e}")

    def _search_persons(self):
        """搜索人员"""
        search = self.search_input.text().strip()
        try:
            persons, total = db.get_all_persons(search=search, include_inactive=True, per_page=200)
            self.person_table.setRowCount(len(persons))

            for row, p in enumerate(persons):
                items = [
                    p.get('name', ''),
                    p.get('employee_id', ''),
                    p.get('department', ''),
                    p.get('position', ''),
                    p.get('phone', ''),
                    "启用" if p.get('status', 1) == 1 else "禁用"
                ]

                for col, text in enumerate(items):
                    item = QTableWidgetItem(str(text) if text else '')
                    item.setTextAlignment(Qt.AlignCenter)
                    self.person_table.setItem(row, col, item)

        except Exception as e:
            logger.error(f"搜索人员失败: {e}")

    # ==================== 人员管理对话框 ====================

    def _add_person_dialog(self):
        """添加人员对话框"""
        dialog = PersonDialog(self, title="添加人员")
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                person_id = db.add_person(**data)
                QMessageBox.information(self, "成功", f"人员 {data['name']} 添加成功 (ID={person_id})")
                self._refresh_persons()
                self._refresh_stats()
                self.lbl_face_count.setText(str(self.face_engine.get_face_count()))

                # 询问是否注册人脸
                reply = QMessageBox.question(self, "注册人脸",
                    "是否现在为此人员注册人脸？\n需要使用摄像头拍照或上传照片。",
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self._register_face_dialog(person_id, data['name'])

            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加失败: {e}")

    def _edit_person_dialog(self, row, col):
        """编辑人员对话框"""
        person_id = self.person_table.item(row, 0).data(Qt.UserRole)
        if person_id is None:
            # 尝试从数据库查找
            name = self.person_table.item(row, 0).text()
            persons, _ = db.get_all_persons(search=name, include_inactive=True)
            if persons:
                person_id = persons[0]['id']

        if person_id is None:
            return

        person = db.get_person(person_id)
        if not person:
            return

        dialog = PersonDialog(self, title="编辑人员", person=person)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                db.update_person(person_id, **data)
                QMessageBox.information(self, "成功", "人员信息已更新")
                self._refresh_persons()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败: {e}")

    def _register_face_dialog(self, person_id, name):
        """注册人脸对话框"""
        dialog = FaceRegisterDialog(self, person_id, name, self.camera)
        if dialog.exec_() == QDialog.Accepted:
            self._load_faces()
            self._refresh_persons()
            self.lbl_face_count.setText(str(self.face_engine.get_face_count()))
            QMessageBox.information(self, "成功", f"{name} 的人脸注册成功")

    # ==================== 人脸加载 ====================

    def _load_faces(self):
        """从数据库加载人脸编码"""
        persons = db.get_persons_with_encoding()
        self.face_engine.load_known_faces(persons)
        logger.info(f"已加载 {len(persons)} 个人脸编码")

    # ==================== 关闭事件 ====================

    def closeEvent(self, event):
        """窗口关闭事件"""
        self._stop_camera()
        event.accept()


# ==================== 人员编辑对话框 ====================

class PersonDialog(QDialog):
    """人员编辑对话框"""

    def __init__(self, parent=None, title="人员信息", person=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.person = person
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入姓名")
        layout.addRow("姓名 *:", self.name_edit)

        self.emp_id_edit = QLineEdit()
        self.emp_id_edit.setPlaceholderText("请输入工号")
        layout.addRow("工号:", self.emp_id_edit)

        self.dept_edit = QLineEdit()
        self.dept_edit.setPlaceholderText("请输入部门")
        layout.addRow("部门:", self.dept_edit)

        self.position_edit = QLineEdit()
        self.position_edit.setPlaceholderText("请输入职位")
        layout.addRow("职位:", self.position_edit)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("请输入电话")
        layout.addRow("电话:", self.phone_edit)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("请输入邮箱")
        layout.addRow("邮箱:", self.email_edit)

        self.remark_edit = QLineEdit()
        self.remark_edit.setPlaceholderText("备注")
        layout.addRow("备注:", self.remark_edit)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_ok.setObjectName("primaryBtn")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

        # 填充已有数据
        if self.person:
            self.name_edit.setText(self.person.get('name', ''))
            self.emp_id_edit.setText(self.person.get('employee_id', '') or '')
            self.dept_edit.setText(self.person.get('department', '') or '')
            self.position_edit.setText(self.person.get('position', '') or '')
            self.phone_edit.setText(self.person.get('phone', '') or '')
            self.email_edit.setText(self.person.get('email', '') or '')
            self.remark_edit.setText(self.person.get('remark', '') or '')

    def get_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'employee_id': self.emp_id_edit.text().strip() or None,
            'department': self.dept_edit.text().strip(),
            'position': self.position_edit.text().strip(),
            'phone': self.phone_edit.text().strip(),
            'email': self.email_edit.text().strip(),
            'remark': self.remark_edit.text().strip(),
        }


# ==================== 人脸注册对话框 ====================

class FaceRegisterDialog(QDialog):
    """人脸注册对话框"""

    def __init__(self, parent=None, person_id=0, name="", camera=None):
        super().__init__(parent)
        self.person_id = person_id
        self.person_name = name
        self.camera = camera
        self.capturing = False
        self.encoding = None

        self.setWindowTitle(f"注册人脸 - {name}")
        self.setMinimumSize(500, 450)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 说明
        info = QLabel(f"为 {self.person_name} 注册人脸\n请正对摄像头，保持光线充足")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("font-size: 16px; padding: 10px; color: #00d4ff;")
        layout.addWidget(info)

        # 摄像头预览
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #0a0a1a; border-radius: 8px;")
        layout.addWidget(self.preview_label)

        # 状态
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # 按钮
        btn_layout = QHBoxLayout()

        self.btn_capture = QPushButton("拍照注册")
        self.btn_capture.setObjectName("successBtn")
        self.btn_capture.setMinimumHeight(40)
        self.btn_capture.clicked.connect(self._capture)
        btn_layout.addWidget(self.btn_capture)

        self.btn_upload = QPushButton("上传照片")
        self.btn_upload.setMinimumHeight(40)
        self.btn_upload.clicked.connect(self._upload_photo)
        btn_layout.addWidget(self.btn_upload)

        btn_cancel = QPushButton("取消")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _capture(self):
        """从摄像头拍照"""
        if not self.camera.is_opened():
            self.status_label.setText("摄像头未打开，正在打开...")
            if not self.camera.open():
                self.status_label.setText("无法打开摄像头")
                return

        self.status_label.setText("正在检测人脸...")
        QApplication.processEvents()

        # 读取几帧
        for _ in range(5):
            ret, frame = self.camera.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.preview_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
                    self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))

        # 检测人脸
        engine = FaceEngine()
        ret, frame = self.camera.read()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locations = engine.detect_faces(rgb)

            if locations:
                # 取最大的人脸
                if len(locations) > 1:
                    areas = [(r - t) * (b - l) for t, r, b, l in locations]
                    best_idx = np.argmax(areas)
                    locations = [locations[best_idx]]

                encoding = engine.encode_face(rgb, locations[0])
                if encoding is not None:
                    self.encoding = encoding
                    self.status_label.setText("人脸检测成功!")
                    self.status_label.setStyleSheet("color: #00ff88; font-size: 16px;")

                    # 绘制人脸框
                    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                    top, right, bottom, left = locations[0]
                    cv2.rectangle(bgr, (left, top), (right, bottom), (0, 255, 0), 3)
                    cv2.putText(bgr, "OK", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                    rgb_result = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_result.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_result.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    self.preview_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
                        self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    ))
                    return

        self.status_label.setText("未检测到人脸，请重试或上传照片")
        self.status_label.setStyleSheet("color: #ff4444; font-size: 16px;")

    def _upload_photo(self):
        """上传照片"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择照片", "", "图片文件 (*.jpg *.jpeg *.png *.bmp)"
        )
        if not filepath:
            return

        self.status_label.setText("正在处理图片...")
        QApplication.processEvents()

        engine = FaceEngine()
        encoding = engine.register_face_from_image(filepath)

        if encoding is not None:
            self.encoding = encoding

            # 显示图片
            pixmap = QPixmap(filepath)
            self.preview_label.setPixmap(pixmap.scaled(
                self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

            self.status_label.setText("人脸检测成功!")
            self.status_label.setStyleSheet("color: #00ff88; font-size: 16px;")
        else:
            self.status_label.setText("未检测到人脸，请使用正面清晰照片")
            self.status_label.setStyleSheet("color: #ff4444; font-size: 16px;")

    def accept(self):
        """确认注册"""
        if self.encoding is None:
            QMessageBox.warning(self, "提示", "请先拍照或上传照片")
            return

        try:
            import uuid
            encoding_blob = pickle.dumps(self.encoding)

            # 保存照片
            ext = '.jpg'
            filename = f"{self.person_id}_{uuid.uuid4().hex[:8]}{ext}"
            filepath = os.path.join(config.FACES_DIR, filename)

            # 从预览标签获取图片
            pixmap = self.preview_label.pixmap()
            if pixmap:
                pixmap.save(filepath)

            db.update_person(self.person_id, face_encoding=encoding_blob, face_image_path=filepath)
            db.add_log("register_face", f"注册人脸: {self.person_name} (ID={self.person_id})")

            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"注册失败: {e}")


# ==================== 启动入口 ====================

def run_pc_app():
    """启动PC端应用"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置暗色主题
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(26, 26, 46))
    palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.Base, QColor(22, 33, 62))
    palette.setColor(QPalette.AlternateBase, QColor(26, 26, 46))
    palette.setColor(QPalette.ToolTipBase, QColor(224, 224, 224))
    palette.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
    palette.setColor(QPalette.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.Button, QColor(22, 33, 62))
    palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
    palette.setColor(QPalette.Highlight, QColor(15, 52, 96))
    palette.setColor(QPalette.HighlightedText, QColor(0, 212, 255))
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.LOG_FILE, encoding='utf-8')
        ]
    )
    run_pc_app()
