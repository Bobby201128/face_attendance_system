# -*- coding: utf-8 -*-
"""
设备命名对话框 - 全屏暗色风格
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton,
                             QWidget, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPainter, QLinearGradient, QColor


class DeviceNameDialog(QDialog):
    """设备命名对话框 - 全屏暗色风格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.device_name = ""
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("设备配置")
        self.setModal(True)

        # 全屏显示
        self.showFullScreen()

        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a1a,
                    stop:0.5 #2a2a2a,
                    stop:1 #1a1a1a
                );
            }
            QLabel {
                color: #e0e0e0;
                background: transparent;
            }
            QLineEdit {
                background: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 8px;
                padding: 15px;
                color: #e0e0e0;
                font-size: 18px;
            }
            QLineEdit:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 18px 60px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #45a049;
            }
            QPushButton:pressed {
                background: #3d8b40;
            }
        """)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(60, 80, 60, 80)

        # 标题
        title = QLabel("欢迎使用人脸识别签到系统")
        title_font = QFont()
        title_font.setPointSize(32)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # 副标题
        subtitle = QLabel("首次运行，请为当前设备命名")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888; font-size: 18px;")
        main_layout.addWidget(subtitle)

        # 网络信息
        try:
            from config import get_network_name
            network_name = get_network_name()
        except:
            network_name = "未知网络"

        network_card = QLabel(f"当前网络: {network_name}")
        network_card.setAlignment(Qt.AlignCenter)
        network_card.setStyleSheet("""
            color: #4CAF50;
            font-size: 16px;
            padding: 12px 30px;
            background: rgba(76, 175, 80, 0.1);
            border: 1px solid rgba(76, 175, 80, 0.3);
            border-radius: 8px;
        """)
        main_layout.addWidget(network_card)

        # 添加间距
        main_layout.addSpacing(60)

        # 输入框容器
        input_container = QFrame()
        input_container.setStyleSheet("""
            QFrame {
                background: #2a2a2a;
                border-radius: 15px;
                padding: 40px;
            }
        """)
        input_layout = QVBoxLayout()
        input_layout.setSpacing(25)

        # 设备名称标签
        name_label = QLabel("设备名称")
        name_label.setStyleSheet("font-size: 16px; color: #888;")
        input_layout.addWidget(name_label)

        # 设备名称输入框
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如：一楼大厅签到机")
        self.name_input.setMaxLength(50)
        self.name_input.setMinimumHeight(60)
        self.name_input.setStyleSheet("""
            QLineEdit {
                font-size: 20px;
                background: #1a1a1a;
                border: 2px solid #404040;
                border-radius: 10px;
                padding: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #4CAF50;
            }
        """)
        input_layout.addWidget(self.name_input)

        # 说明文本
        info = QLabel("设备名称将用于手机端识别和连接此设备")
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 14px; padding: 10px;")
        input_layout.addWidget(info)

        input_container.setLayout(input_layout)
        main_layout.addWidget(input_container)

        # 添加弹性空间
        main_layout.addStretch()

        # 按钮容器
        button_container = QHBoxLayout()
        button_container.addStretch()

        ok_button = QPushButton("确定")
        ok_button.setFixedWidth(200)
        ok_button.setFixedHeight(60)
        ok_button.clicked.connect(self.accept_name)
        button_container.addWidget(ok_button)

        button_container.addStretch()

        main_layout.addLayout(button_container)

        # 底部间距
        main_layout.addSpacing(40)

        self.setLayout(main_layout)

        # 设置焦点到输入框
        self.name_input.setFocus()

    def accept_name(self):
        """确认设备名称"""
        name = self.name_input.text().strip()
        if not name:
            self.name_input.setStyleSheet("""
                QLineEdit {
                    font-size: 20px;
                    background: #1a1a1a;
                    border: 2px solid #e74c3c;
                    border-radius: 10px;
                    padding: 20px;
                }
            """)
            return

        if len(name) < 2:
            self.name_input.setStyleSheet("""
                QLineEdit {
                    font-size: 20px;
                    background: #1a1a1a;
                    border: 2px solid #e74c3c;
                    border-radius: 10px;
                    padding: 20px;
                }
            """)
            return

        self.device_name = name
        self.accept()

    def get_device_name(self):
        """获取设备名称"""
        return self.device_name

    def keyPressEvent(self, event):
        """支持回车键确认"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.accept_name()
        else:
            super().keyPressEvent(event)
