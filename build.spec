# -*- mode: python ; coding: utf-8 -*-
import os
import sys

BASE_DIR = os.path.abspath('.')

# 禁用 dlib CUDA，避免打包时 cudnn DLL 崩溃
os.environ['DLIB_USE_CUDA'] = '0'

a = Analysis(
    ['main.py'],
    pathex=[BASE_DIR],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('local_mobile.html', '.'),
        ('icon.png', '.'),
        # 打包 face_recognition 模型文件
        (sys.base_prefix + '/lib/site-packages/face_recognition_models/models',
         'face_recognition_models/models'),
    ],
    hiddenimports=[
        'flask_cors',
        'flask_jwt_extended',
        'openpyxl',
        'face_recognition_models',
        'cv2',
        'numpy',
        'sqlite3',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtSvg',
    ],
    excludes=[
        'matplotlib',
        'tkinter',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'PyQt6',
        'PySide6',
        'PySide2',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='智脸考勤',
    icon='icon.ico',
    console=False,
    onefile=True,
)
