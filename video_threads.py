import time
import threading
import logging

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class VideoThread(QThread):
    """视频捕获线程 - 高性能显示"""
    frame_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, camera_manager):
        super().__init__()
        self.camera = camera_manager
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            ret, frame = self.camera.read()
            if ret:
                self.frame_signal.emit(frame)
            else:
                time.sleep(0.01)  # 更快的错误恢复

    def stop(self):
        self.running = False
        self.wait()


class RecognitionThread(QThread):
    """人脸识别线程 - 优化版：快速响应+高准确率"""
    result_signal = pyqtSignal(list)

    def __init__(self, face_engine):
        super().__init__()
        self.face_engine = face_engine
        self.running = False
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.process_interval = 1  # 每次都处理，不再跳过
        self.frame_count = 0
        self.last_results = []  # 缓存上一次结果

    def update_frame(self, frame):
        """更新最新帧 - 轻量级操作"""
        if frame is not None and self.running:
            # 直接引用，不复制（读取时再复制）
            with self.frame_lock:
                self.latest_frame = frame

    def run(self):
        self.running = True
        while self.running:
            self.frame_count += 1
            
            # 每次循环处理最新帧，保证响应速度
            if self.frame_count % self.process_interval == 0:
                with self.frame_lock:
                    if self.latest_frame is not None:
                        # 只在需要处理时才复制
                        frame_to_process = self.latest_frame.copy()
                    else:
                        continue
                
                try:
                    # 执行识别
                    results = self.face_engine.process_frame(frame_to_process)
                    
                    # 只有结果有效才更新
                    if results:
                        self.last_results = results
                        self.result_signal.emit(results)
                        
                except Exception as e:
                    logger.error(f"识别错误: {e}")
            
            # 短暂休眠，让出CPU
            time.sleep(0.02)  # 约15Hz识别频率

    def stop(self):
        self.running = False
        self.wait()
