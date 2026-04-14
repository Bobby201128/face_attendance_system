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
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d4ff;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 环境列表
        self.env_list = QListWidget()
        self.env_list.setIconSize(QSize(32, 32))
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
        self.select_btn.setStyleSheet("background-color: #00d4ff; color: #1a1a2e; font-weight: bold;")

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
                item = QListWidgetItem(f"📍 {env['name']}")
                item.setData(Qt.UserRole, env)

                # 标记默认环境
                if env.get('default_env'):
                    item.setText(f"⭐ {env['name']} (默认)")

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


# ==================== 人脸审核对话框 ====================

class FaceApprovalDialog(QDialog):
    """人脸审核对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_face_id = None
        self.faces_data = []
        self.current_index = 0
        self._init_ui()
        self._load_pending_faces()

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle("人脸审核")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_pending_faces)

        self.count_label = QLabel("待审核: 0")
        self.count_label.setStyleSheet("font-size: 14px; color: #ff9100;")

        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.count_label)
        layout.addLayout(toolbar)

        # 主内容区 - 左右分割
        main_splitter = QHBoxLayout()

        # 左侧：列表
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("待审核列表:"))

        self.faces_list = QListWidget()
        self.faces_list.setIconSize(QSize(48, 48))
        self.faces_list.itemClicked.connect(self._on_face_selected)
        left_panel.addWidget(self.faces_list)

        main_splitter.addLayout(left_panel, 1)

        # 右侧：详情
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("人脸详情:"))

        # 人脸图片
        self.image_label = QLabel()
        self.image_label.setMinimumSize(200, 200)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #0f3460; border-radius: 8px;")
        self.image_label.setWordWrap(True)
        right_panel.addWidget(self.image_label)

        # 信息表单
        info_group = QGroupBox("人员信息")
        info_layout = QFormLayout()

        self.person_name_label = QLabel("-")
        self.person_emp_id_label = QLabel("-")
        self.upload_time_label = QLabel("-")
        self.upload_source_label = QLabel("-")

        info_layout.addRow("姓名:", self.person_name_label)
        info_layout.addRow("工号:", self.person_emp_id_label)
        info_layout.addRow("上传时间:", self.upload_time_label)
        info_layout.addRow("来源:", self.upload_source_label)

        info_group.setLayout(info_layout)
        right_panel.addWidget(info_group)

        # 拒绝原因
        reason_group = QGroupBox("拒绝原因（如拒绝）")
        reason_layout = QVBoxLayout()
        self.reject_reason = QTextEdit()
        self.reject_reason.setMaximumHeight(60)
        self.reject_reason.setPlaceholderText("请输入拒绝原因...")
        reason_layout.addWidget(self.reject_reason)
        reason_group.setLayout(reason_layout)
        right_panel.addWidget(reason_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.approve_btn = QPushButton("✅ 批准")
        self.approve_btn.setStyleSheet("background-color: #00c853; color: white; font-weight: bold; padding: 10px;")
        self.approve_btn.clicked.connect(self._approve_face)

        self.reject_btn = QPushButton("❌ 拒绝")
        self.reject_btn.setStyleSheet("background-color: #ff1744; color: white; font-weight: bold; padding: 10px;")
        self.reject_btn.clicked.connect(self._reject_face)

        button_layout.addStretch()
        button_layout.addWidget(self.approve_btn)
        button_layout.addWidget(self.reject_btn)
        right_panel.addLayout(button_layout)

        main_splitter.addLayout(right_panel, 2)
        layout.addLayout(main_splitter)

        # 初始禁用按钮
        self.approve_btn.setEnabled(False)
        self.reject_btn.setEnabled(False)

    def _load_pending_faces(self):
        """加载待审核人脸"""
        try:
            faces, total = db.get_pending_faces(page=1, per_page=50)

            self.faces_data = faces
            self.faces_list.clear()

            if not faces:
                self.count_label.setText("待审核: 0")
                self.image_label.setText("暂无待审核人脸")
                return

            self.count_label.setText(f"待审核: {total}")

            for idx, face in enumerate(faces):
                # 加载缩略图
                try:
                    if face.get('image_path') and os.path.exists(face['image_path']):
                        pixmap = QPixmap(face['image_path'])
                        icon = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    else:
                        icon = QPixmap()

                    item = QListWidgetItem(f"{face['person_name']} ({face.get('employee_id') or '无工号'})")
                    item.setIcon(icon)
                    item.setData(Qt.UserRole, face)
                    self.faces_list.addItem(item)
                except Exception as e:
                    logger.error(f"加载人脸缩略图失败: {e}")

            # 默认选择第一个
            if self.faces_list.count() > 0:
                self.faces_list.setCurrentRow(0)
                self._on_face_selected(self.faces_list.item(0))

        except Exception as e:
            logger.error(f"加载待审核人脸失败: {e}")
            QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")

    def _on_face_selected(self, item):
        """人脸被选择"""
        face = item.data(Qt.UserRole)
        self.current_face_id = face['id']

        # 显示图片
        try:
            if face.get('image_path') and os.path.exists(face['image_path']):
                pixmap = QPixmap(face['image_path'])
                scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("图片不存在")
        except Exception as e:
            logger.error(f"显示人脸图片失败: {e}")
            self.image_label.setText("图片加载失败")

        # 显示信息
        self.person_name_label.setText(face['person_name'])
        self.person_emp_id_label.setText(face.get('employee_id') or '无')

        try:
            upload_time = datetime.fromisoformat(face['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            self.upload_time_label.setText(upload_time)
        except:
            self.upload_time_label.setText(face.get('created_at', '-'))

        source_map = {'mobile': '手机端', 'pc': 'PC端'}
        self.upload_source_label.setText(source_map.get(face.get('upload_source', 'mobile'), '未知'))

        # 启用按钮
        self.approve_btn.setEnabled(True)
        self.reject_btn.setEnabled(True)

    def _approve_face(self):
        """批准人脸"""
        if not self.current_face_id:
            return

        try:
            success, message = db.approve_face_image(self.current_face_id, 1)
            if success:
                QMessageBox.information(self, "成功", "人脸已批准")
                self._load_pending_faces()  # 重新加载列表
            else:
                QMessageBox.warning(self, "失败", message)
        except Exception as e:
            logger.error(f"批准人脸失败: {e}")
            QMessageBox.critical(self, "错误", f"批准失败: {str(e)}")

    def _reject_face(self):
        """拒绝人脸"""
        if not self.current_face_id:
            return

        reason = self.reject_reason.toPlainText().strip()
        if not reason:
            QMessageBox.warning(self, "提示", "请输入拒绝原因")
            return

        try:
            db.reject_face_image(self.current_face_id, reason)
            QMessageBox.information(self, "成功", "人脸已拒绝")
            self.reject_reason.clear()
            self._load_pending_faces()  # 重新加载列表
        except Exception as e:
            logger.error(f"拒绝人脸失败: {e}")
            QMessageBox.critical(self, "错误", f"拒绝失败: {str(e)}")


# ==================== 人员环境关联对话框 ====================

class PersonEnvironmentDialog(QDialog):
    """人员环境关联对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle("人员环境管理")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 顶部筛选区
        filter_bar = QHBoxLayout()

        filter_bar.addWidget(QLabel("环境:"))
        self.env_combo = QComboBox()
        self.env_combo.currentIndexChanged.connect(self._on_env_changed)
        filter_bar.addWidget(self.env_combo)

        filter_bar.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入姓名或工号搜索...")
        self.search_input.textChanged.connect(self._filter_persons)
        filter_bar.addWidget(self.search_input)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._load_data)
        filter_bar.addWidget(refresh_btn)

        layout.addLayout(filter_bar)

        # 主内容区 - 左右分割
        main_splitter = QHBoxLayout()

        # 左侧：可选人员列表
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("📋 可选人员 (双击添加):"))

        self.available_list = QListWidget()
        self.available_list.itemDoubleClicked.connect(self._add_person_to_env)
        self.available_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        left_panel.addWidget(self.available_list)

        add_selected_btn = QPushButton("➡ 添加选中人员")
        add_selected_btn.clicked.connect(self._add_selected_persons)
        left_panel.addWidget(add_selected_btn)

        main_splitter.addLayout(left_panel, 1)

        # 右侧：已关联人员列表
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("✅ 已关联人员 (双击移除):"))

        self.assigned_list = QListWidget()
        self.assigned_list.itemDoubleClicked.connect(self._remove_person_from_env)
        self.assigned_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        right_panel.addWidget(self.assigned_list)

        remove_selected_btn = QPushButton("❌ 移除选中人员")
        remove_selected_btn.clicked.connect(self._remove_selected_persons)
        right_panel.addWidget(remove_selected_btn)

        main_splitter.addLayout(right_panel, 1)

        layout.addLayout(main_splitter)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def _load_data(self):
        """加载数据"""
        try:
            # 加载环境列表
            environments = db.get_all_environments(include_inactive=False)
            self.env_combo.clear()

            for env in environments:
                self.env_combo.addItem(env['name'], env['id'])

            if environments:
                self._load_environment_persons(environments[0]['id'])

        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            QMessageBox.critical(self, "错误", f"加载数据失败: {str(e)}")

    def _on_env_changed(self, index):
        """环境切换"""
        if index >= 0:
            env_id = self.env_combo.itemData(index)
            self._load_environment_persons(env_id)

    def _load_environment_persons(self, env_id):
        """加载环境的人员"""
        try:
            # 获取已关联的人员
            assigned_persons = db.get_environment_persons(env_id)
            assigned_ids = {p['id'] for p in assigned_persons}

            # 获取所有活跃人员
            all_persons, _ = db.get_all_persons(include_inactive=False, per_page=1000)

            # 更新列表
            self.available_list.clear()
            self.assigned_list.clear()

            for person in all_persons:
                item_text = f"{person['name']} ({person.get('employee_id') or '无工号'})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, person)

                if person['id'] in assigned_ids:
                    # 已关联
                    self.assigned_list.addItem(item)
                else:
                    # 未关联
                    self.available_list.addItem(item)

            self._filter_persons()

        except Exception as e:
            logger.error(f"加载环境人员失败: {e}")

    def _filter_persons(self):
        """过滤人员"""
        search_text = self.search_input.text().lower()

        # 过滤可选人员
        for i in range(self.available_list.count()):
            item = self.available_list.item(i)
            person = item.data(Qt.UserRole)
            text = f"{person['name']} {person.get('employee_id', '')}".lower()
            item.setHidden(search_text not in text)

        # 过滤已关联人员
        for i in range(self.assigned_list.count()):
            item = self.assigned_list.item(i)
            person = item.data(Qt.UserRole)
            text = f"{person['name']} {person.get('employee_id', '')}".lower()
            item.setHidden(search_text not in text)

    def _add_person_to_env(self, item):
        """添加人员到环境"""
        try:
            person = item.data(Qt.UserRole)
            env_id = self.env_combo.currentData()

            if env_id:
                db.add_person_to_environment(person['id'], env_id, is_primary=0)

                # 移动到已关联列表
            row = self.available_list.row(item)
            self.available_list.takeItem(row)
            self.assigned_list.addItem(item)

        except Exception as e:
            logger.error(f"添加人员到环境失败: {e}")

    def _add_selected_persons(self):
        """添加选中的人员"""
        selected_items = self.available_list.selectedItems()
        for item in selected_items:
            self._add_person_to_env(item)

    def _remove_person_from_env(self, item):
        """从环境移除人员"""
        try:
            person = item.data(Qt.UserRole)
            env_id = self.env_combo.currentData()

            if env_id:
                db.remove_person_from_environment(person['id'], env_id)

                # 移动到可选列表
                row = self.assigned_list.row(item)
                self.assigned_list.takeItem(row)
                self.available_list.addItem(item)

        except Exception as e:
            logger.error(f"从环境移除人员失败: {e}")

    def _remove_selected_persons(self):
        """移除选中的人员"""
        selected_items = self.assigned_list.selectedItems()
        for item in selected_items:
            self._remove_person_from_env(item)


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

    @staticmethod
    def show_face_approval_dialog(parent=None):
        """显示人脸审核对话框"""
        dialog = FaceApprovalDialog(parent)
        dialog.exec_()

    @staticmethod
    def show_person_environment_dialog(parent=None):
        """显示人员环境关联对话框"""
        dialog = PersonEnvironmentDialog(parent)
        dialog.exec_()


# ==================== 工具函数 ====================

def create_extension_menu(main_window):
    """在主窗口中创建扩展功能菜单"""

    # 在主窗口的工具栏或菜单栏添加新功能按钮
    # 这个函数需要在主窗口初始化后调用

    try:
        # 获取主窗口的工具栏或创建新工具栏
        if hasattr(main_window, 'toolbar'):
            toolbar = main_window.toolbar
        else:
            toolbar = main_window.addToolBar("扩展功能")
            toolbar.setMovable(False)

        # 添加功能按钮
        face_approval_btn = QPushButton("👤 人脸审核")
        face_approval_btn.clicked.connect(lambda: PCUIExtensions.show_face_approval_dialog(main_window))
        toolbar.addWidget(face_approval_btn)

        person_env_btn = QPushButton("🏢 人员环境")
        person_env_btn.clicked.connect(lambda: PCUIExtensions.show_person_environment_dialog(main_window))
        toolbar.addWidget(person_env_btn)

        logger.info("扩展功能菜单已添加")

    except Exception as e:
        logger.error(f"创建扩展菜单失败: {e}")
