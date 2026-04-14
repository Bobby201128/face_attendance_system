# -*- coding: utf-8 -*-
"""
PC端UI扩展模块 - 阶段4新功能
包含环境选择、人脸审核、人员环境关联等新UI组件
"""
import os
import logging
import base64
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QTextEdit, QGroupBox, QFormLayout, QSpinBox,
    QCheckBox, QFileDialog, QMessageBox, QProgressBar, QScrollArea,
    QWidget, QListWidget, QListWidgetItem, QFrame, QSizePolicy,
    QGridLayout, QAbstractItemView, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from database import db

logger = logging.getLogger(__name__)


# ==================== 环境选择对话框 ====================

class EnvironmentDialog(QDialog):
    """环境选择对话框 - PC启动时显示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_environment = None
        self._init_ui()
        self._load_environments()

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle("选择签到环境")
        self.setModal(True)
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标题
        title_label = QLabel("选择签到环境")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 环境列表
        self.env_list = QListWidget()
        self.env_list.itemClicked.connect(self._on_env_selected)
        layout.addWidget(QLabel("可用环境:"))
        layout.addWidget(self.env_list)

        # 环境详情
        self.details_group = QGroupBox("环境详情")
        details_layout = QFormLayout()

        self.name_label = QLabel("-")
        self.desc_label = QLabel("-")
        self.work_time_label = QLabel("-")
        self.sign_mode_label = QLabel("-")

        details_layout.addRow("环境名称:", self.name_label)
        details_layout.addRow("描述:", self.desc_label)
        details_layout.addRow("工作时间:", self.work_time_label)
        details_layout.addRow("签到模式:", self.sign_mode_label)

        self.details_group.setLayout(details_layout)
        layout.addWidget(self.details_group)

        # 按钮
        button_layout = QHBoxLayout()
        self.select_btn = QPushButton("选择环境")
        self.select_btn.clicked.connect(self._on_select)
        self.select_btn.setEnabled(False)
        self.select_btn.setStyleSheet("background-color: #404040; color: #e0e0e0; font-weight: bold;")

        cancel_btn = QPushButton("退出")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.select_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def _load_environments(self):
        """加载环境列表"""
        try:
            environments = db.get_all_environments(include_inactive=False)

            if not environments:
                QMessageBox.warning(self, "提示", "没有可用的环境，请先在手机端创建环境")
                return

            for env in environments:
                # 标记默认环境
                if env.get('default_env'):
                    item = QListWidgetItem(f"{env['name']} (默认)")
                else:
                    item = QListWidgetItem(env['name'])

                item.setData(Qt.UserRole, env)
                self.env_list.addItem(item)

            # 默认选择第一个
            if self.env_list.count() > 0:
                self.env_list.setCurrentRow(0)
                self._on_env_selected(self.env_list.item(0))

        except Exception as e:
            logger.error(f"加载环境列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载环境列表失败: {str(e)}")

    def _on_env_selected(self, item):
        """环境被选择"""
        env = item.data(Qt.UserRole)
        self.selected_environment = env

        # 更新详情
        self.name_label.setText(env['name'])
        self.desc_label.setText(env.get('description') or '无描述')

        work_time = f"{env['work_start_hour']:02d}:{env['work_start_minute']:02d} - " \
                    f"{env['work_end_hour']:02d}:{env['work_end_minute']:02d}"
        self.work_time_label.setText(work_time)

        sign_mode = "自动签到" if env['sign_mode'] == 'auto' else "手动签到"
        self.sign_mode_label.setText(sign_mode)

        # 启用选择按钮
        self.select_btn.setEnabled(True)

    def _on_select(self):
        """确认选择"""
        if self.selected_environment:
            logger.info(f"选择环境: {self.selected_environment['name']}")
            self.accept()

    def get_selected_environment(self):
        """获取选择的环境"""
        return self.selected_environment


# ==================== PC UI 扩展功能 ====================

class PCUIExtensions:
    """PC界面扩展功能集合"""

    @staticmethod
    def show_environment_dialog(parent=None):
        """显示环境选择对话框"""
        dialog = EnvironmentDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            return dialog.get_selected_environment()
        return None


# ==================== 工具函数 ====================
