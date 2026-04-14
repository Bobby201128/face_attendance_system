# -*- coding: utf-8 -*-
"""
人脸识别签到系统 - 人脸识别引擎
基于 face_recognition 库，支持多种识别模式
"""
import os
import logging
import threading
import time
import pickle
from collections import deque

import cv2
import numpy as np

import config

logger = logging.getLogger(__name__)


class FaceEngine:
    """人脸识别引擎"""

    def __init__(self):
        self.face_detector = None
        self.pose_predictor = None
        self.face_encoder = None
        self.known_faces = []       # [(encoding, person_id, name), ...]
        self.known_names = []
        self.known_ids = []
        self.known_encodings = []

        # 识别状态
        self._lock = threading.Lock()
        self._last_sign_times = {}  # person_id -> last_sign_timestamp
        self._confirm_counters = {}  # person_id -> consecutive_match_count

        # 识别模式参数
        self._mode_configs = {
            "fast": {
                "model": "hog",
                "upsample": 0,
                "num_jitters": 1,
            },
            "balanced": {
                "model": "hog",
                "upsample": 1,
                "num_jitters": 2,
            },
            "accurate": {
                "model": "cnn",
                "upsample": 1,
                "num_jitters": 3,
            }
        }

        self._current_mode = config.RECOGNITION_MODE
        self._threshold = config.RECOGNITION_THRESHOLD
        self._confirm_frames = config.CONFIRM_FRAMES
        self._cooldown = config.SIGN_COOLDOWN

        # 编码缓存文件
        self._cache_path = os.path.join(config.DATA_DIR, "face_cache.pkl")

        # 初始化
        self._init_models()

    def _init_models(self):
        """初始化人脸识别模型"""
        try:
            import face_recognition
            self.face_encoder = face_recognition
            logger.info("face_recognition 库加载成功")
        except ImportError:
            logger.error("=" * 60)
            logger.error("face_recognition 库未安装！")
            logger.error("=" * 60)
            logger.error("人脸识别功能需要安装 face_recognition 库。")
            logger.error("")
            logger.error("安装方法:")
            logger.error("  方法1 - 使用 conda（推荐）:")
            logger.error("    conda install -c conda-forge dlib")
            logger.error("    pip install face-recognition")
            logger.error("")
            logger.error("  方法2 - 手动安装:")
            logger.error("    下载并安装 Visual Studio Build Tools")
            logger.error("    pip install dlib")
            logger.error("    pip install face-recognition")
            logger.error("")
            logger.error("如果不使用人脸识别功能，可以忽略此错误。")
            logger.error("=" * 60)
            raise

    def load_known_faces(self, persons_data):
        """从数据库加载已知人脸编码

        Args:
            persons_data: list of dict, 每个包含 id, name, face_encoding
        """
        with self._lock:
            self.known_faces = []
            self.known_names = []
            self.known_ids = []
            self.known_encodings = []

            for person in persons_data:
                encoding_blob = person.get('face_encoding')
                if encoding_blob is None:
                    continue

                try:
                    encoding = pickle.loads(encoding_blob) if isinstance(encoding_blob, (bytes, bytearray)) else encoding_blob
                    encoding = np.array(encoding, dtype=np.float64)
                    self.known_encodings.append(encoding)
                    self.known_names.append(person['name'])
                    self.known_ids.append(person['id'])
                except Exception as e:
                    logger.warning(f"加载人脸编码失败 (ID={person['id']}): {e}")

            self.known_faces = list(zip(self.known_encodings, self.known_ids, self.known_names))
            logger.info(f"已加载 {len(self.known_faces)} 个人脸编码")

    def _validate_image(self, image):
        """验证并标准化图像为 face_recognition 要求的格式 (uint8, contiguous, RGB)

        Args:
            image: 输入图像

        Returns:
            标准化后的图像 (numpy uint8 RGB, 3通道), 或 None 表示无效
        """
        if image is None:
            logger.debug("图像验证失败: 输入为 None")
            return None
        try:
            if not isinstance(image, np.ndarray):
                image = np.asarray(image)

            if image.size == 0 or 0 in image.shape:
                logger.debug(f"图像验证失败: 无效的图像尺寸 - shape: {image.shape}, size: {image.size}")
                return None

            original_dtype = image.dtype
            original_shape = image.shape

            if image.dtype != np.uint8:
                if image.dtype in [np.float32, np.float64]:
                    img_max = image.max()
                    if img_max <= 1.0:
                        image = (image * 255).astype(np.uint8)
                    else:
                        image = image.astype(np.uint8)
                else:
                    image = image.astype(np.uint8)

            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif len(image.shape) == 3:
                if image.shape[2] == 4:
                    image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
                elif image.shape[2] == 1:
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
                elif image.shape[2] != 3:
                    logger.debug(f"图像验证失败: 不支持的通道数 - {image.shape}")
                    return None
            else:
                logger.debug(f"图像验证失败: 不支持的维度 - {image.shape}")
                return None

            if not image.flags['C_CONTIGUOUS']:
                image = np.ascontiguousarray(image)

            # 最终验证
            if image.dtype != np.uint8 or len(image.shape) != 3 or image.shape[2] != 3:
                logger.debug(f"图像验证失败: 最终格式不正确 - dtype: {image.dtype}, shape: {image.shape}")
                return None

            return image

        except Exception as e:
            logger.debug(f"图像验证异常: {e}, 原始类型: {type(image)}, 原始shape: {getattr(image, 'shape', 'N/A')}")
            return None

    def encode_face(self, image, face_location=None):
        """对单张人脸图像进行编码

        Args:
            image: numpy数组 (RGB格式)
            face_location: (top, right, bottom, left) 人脸位置

        Returns:
            encoding or None
        """
        try:
            image = self._validate_image(image)
            if image is None:
                logger.warning("人脸编码失败: 图像验证未通过")
                return None

            mode_config = self._mode_configs.get(self._current_mode, self._mode_configs['balanced'])
            if face_location:
                encoding = self.face_encoder.face_encodings(
                    image, [face_location], num_jitters=mode_config['num_jitters']
                )
            else:
                encoding = self.face_encoder.face_encodings(
                    image, num_jitters=mode_config['num_jitters']
                )

            return encoding[0] if encoding else None
        except Exception as e:
            logger.error(f"人脸编码失败: {e}, 图像shape: {image.shape if image is not None else 'N/A'}")
            return None

    def detect_faces(self, image):
        """检测图像中的人脸

        Args:
            image: numpy数组 (RGB格式)

        Returns:
            list of (top, right, bottom, left)
        """
        try:
            image = self._validate_image(image)
            if image is None:
                logger.warning("人脸检测失败: 图像验证未通过")
                return []

            # 详细检查图像属性
            logger.debug(f"检测图像属性 - shape: {image.shape}, dtype: {image.dtype}, "
                        f"C_CONTIGUOUS: {image.flags['C_CONTIGUOUS']}, "
                        f"min: {image.min()}, max: {image.max()}")

            # 额外的安全保障：确保图像格式完全正确
            if not image.flags['C_CONTIGUOUS']:
                image = np.ascontiguousarray(image)
                logger.debug("重新创建连续数组")

            if image.dtype != np.uint8:
                logger.warning(f"图像数据类型不正确: {image.dtype}, 转换为 uint8")
                image = image.astype(np.uint8)

            # 最终检查
            if len(image.shape) != 3 or image.shape[2] != 3:
                logger.error(f"图像维度不正确: {image.shape}")
                return []

            mode_config = self._mode_configs.get(self._current_mode, self._mode_configs['balanced'])
            face_locations = self.face_encoder.face_locations(
                image,
                model=mode_config['model'],
                number_of_times_to_upsample=mode_config['upsample']
            )
            return face_locations
        except Exception as e:
            logger.error(f"人脸检测失败: {e}, 图像shape: {image.shape if image is not None else 'N/A'}, "
                        f"dtype: {image.dtype if image is not None else 'N/A'}")
            return []

    def recognize_face(self, image, face_location):
        """识别单张人脸

        Args:
            image: numpy数组 (RGB格式)
            face_location: (top, right, bottom, left)

        Returns:
            dict: {
                'matched': bool,
                'person_id': int or None,
                'name': str or None,
                'confidence': float,
                'confirmed': bool
            }
        """
        encoding = self.encode_face(image, face_location)
        if encoding is None:
            return {'matched': False, 'person_id': None, 'name': None, 'confidence': 0, 'confirmed': False}

        with self._lock:
            if not self.known_encodings:
                return {'matched': False, 'person_id': None, 'name': None, 'confidence': 0, 'confirmed': False}

            # 计算距离
            distances = self.face_encoder.face_distance(self.known_encodings, encoding)

            best_idx = int(np.argmin(distances))
            best_distance = distances[best_idx]
            best_confidence = 1.0 - best_distance

            if best_confidence >= self._threshold:
                person_id = self.known_ids[best_idx]
                name = self.known_names[best_idx]

                # 检查冷却时间
                now = time.time()
                last_time = self._last_sign_times.get(person_id, 0)
                if now - last_time < self._cooldown:
                    return {
                        'matched': True,
                        'person_id': person_id,
                        'name': name,
                        'confidence': best_confidence,
                        'confirmed': False,
                        'cooldown': True
                    }

                # 连续确认计数
                self._confirm_counters[person_id] = self._confirm_counters.get(person_id, 0) + 1
                confirmed = self._confirm_counters[person_id] >= self._confirm_frames

                if confirmed:
                    self._confirm_counters[person_id] = 0
                    self._last_sign_times[person_id] = now

                return {
                    'matched': True,
                    'person_id': person_id,
                    'name': name,
                    'confidence': best_confidence,
                    'confirmed': confirmed
                }
            else:
                return {
                    'matched': False,
                    'person_id': None,
                    'name': None,
                    'confidence': best_confidence,
                    'confirmed': False
                }

    def process_frame(self, frame):
        """处理一帧图像，检测并识别人脸

        Args:
            frame: BGR格式的numpy数组

        Returns:
            list of dict: 每个识别到的人脸信息
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return []

        try:
            # 确保 frame 是有效格式
            if frame.size == 0 or 0 in frame.shape:
                return []

            # 转换为 RGB
            if len(frame.shape) == 2:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            elif len(frame.shape) == 3:
                if frame.shape[2] == 4:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                elif frame.shape[2] == 1:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                else:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                return []

            # 确保数据类型正确
            if rgb_frame.dtype != np.uint8:
                if rgb_frame.dtype in [np.float32, np.float64]:
                    if rgb_frame.max() <= 1.0:
                        rgb_frame = np.clip(rgb_frame * 255, 0, 255).astype(np.uint8)
                    else:
                        rgb_frame = np.clip(rgb_frame, 0, 255).astype(np.uint8)
                else:
                    rgb_frame = np.clip(rgb_frame, 0, 255).astype(np.uint8)

            # 确保是连续数组
            if not rgb_frame.flags['C_CONTIGUOUS']:
                rgb_frame = np.ascontiguousarray(rgb_frame)

            # 验证转换后的图像
            if rgb_frame.size == 0 or rgb_frame.shape[2] != 3:
                logger.warning(f"转换后的图像无效 - size: {rgb_frame.size}, shape: {rgb_frame.shape}")
                return []

            # 强制确保RGB图像是连续的
            rgb_frame = np.ascontiguousarray(rgb_frame, dtype=np.uint8)

            logger.debug(f"RGB图像 - shape: {rgb_frame.shape}, dtype: {rgb_frame.dtype}, "
                        f"C_CONTIGUOUS: {rgb_frame.flags['C_CONTIGUOUS']}")

            # 缩小图像以加快检测速度
            # 注意：使用不同的插值方法可能影响结果
            small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

            logger.debug(f"缩小后的图像 - shape: {small_frame.shape}, dtype: {small_frame.dtype}, "
                        f"C_CONTIGUOUS: {small_frame.flags['C_CONTIGUOUS']}")

            # 强制创建一个新的连续数组，确保内存布局正确
            small_frame = np.ascontiguousarray(small_frame, dtype=np.uint8)

            logger.debug(f"强制连续后 - shape: {small_frame.shape}, dtype: {small_frame.dtype}, "
                        f"C_CONTIGUOUS: {small_frame.flags['C_CONTIGUOUS']}")

            # 最终验证
            if small_frame.dtype != np.uint8 or len(small_frame.shape) != 3 or small_frame.shape[2] != 3:
                logger.error(f"缩小图像最终格式不正确 - dtype: {small_frame.dtype}, shape: {small_frame.shape}")
                return []

            small_face_locations = self.detect_faces(small_frame)

            results = []
            for small_loc in small_face_locations:
                # 将检测到的人脸位置放大回原图尺寸
                top, right, bottom, left = small_loc
                top *= 2
                right *= 2
                bottom *= 2
                left *= 2
                face_location = (top, right, bottom, left)

                # 使用原图进行特征编码以保证准确率
                result = self.recognize_face(rgb_frame, face_location)
                result['location'] = face_location
                results.append(result)

            # 清理过期的确认计数器 (超过5秒未匹配的)
            current_time = time.time()
            expired_ids = [pid for pid, count in self._confirm_counters.items() if count > 0]
            for pid in expired_ids:
                if pid not in [r['person_id'] for r in results if r['matched']]:
                    self._confirm_counters[pid] = max(0, self._confirm_counters.get(pid, 0) - 1)

            return results

        except Exception as e:
            logger.error(f"处理帧时出错: {e}, frame shape: {frame.shape if frame is not None else None}, dtype: {frame.dtype if frame is not None else None}")
            return []

    def draw_results(self, frame, results, show_confidence=True):
        """在帧上绘制识别结果（优化版）

        Args:
            frame: BGR格式图像
            results: process_frame的返回结果
            show_confidence: 是否显示置信度

        Returns:
            绘制后的BGR图像（直接在原图像上修改）
        """
        # 直接在原图像上绘制，避免复制
        for result in results:
            top, right, bottom, left = result['location']
            name = result.get('name', 'Unknown')
            confidence = result.get('confidence', 0)
            confirmed = result.get('confirmed', False)
            matched = result.get('matched', False)
            cooldown = result.get('cooldown', False)

            if matched and confirmed:
                # 签到成功 - 绿色
                color = (0, 255, 0)
                label = f"{name} ({confidence:.0%})"
            elif matched and cooldown:
                # 冷却中 - 黄色
                color = (0, 255, 255)
                label = f"{name} (已签到)"
            elif matched:
                # 识别中 - 蓝色
                count = self._confirm_counters.get(result['person_id'], 0)
                color = (255, 165, 0)
                label = f"{name} ({count}/{self._confirm_frames})"
            else:
                # 未知 - 红色
                color = (0, 0, 255)
                label = "Unknown"

            # 绘制人脸框
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # 绘制标签背景
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 1

            (text_width, text_height), baseline = cv2.getTextSize(
                label, font, font_scale, thickness
            )

            label_y = top - 10 if top - 10 > text_height else bottom + text_height + 10

            cv2.rectangle(
                frame,
                (left, label_y - text_height - 5),
                (left + text_width + 10, label_y + 5),
                color,
                -1
            )
            cv2.putText(
                frame, label,
                (left + 5, label_y - 3),
                font, font_scale, (255, 255, 255), thickness
            )

        return frame

    def set_mode(self, mode):
        """设置识别模式"""
        if mode in self._mode_configs:
            self._current_mode = mode
            logger.info(f"识别模式切换为: {mode}")
            return True
        return False

    def set_threshold(self, threshold):
        """设置识别阈值"""
        self._threshold = max(0.1, min(1.0, threshold))
        logger.info(f"识别阈值设置为: {self._threshold}")
        return self._threshold

    def set_confirm_frames(self, frames):
        """设置确认帧数"""
        self._confirm_frames = max(1, min(10, frames))
        return self._confirm_frames

    def set_cooldown(self, seconds):
        """设置签到冷却时间"""
        self._cooldown = max(0, seconds)
        return self._cooldown

    def reset_cooldown(self, person_id=None):
        """重置冷却时间"""
        if person_id:
            self._last_sign_times.pop(person_id, None)
        else:
            self._last_sign_times.clear()
            self._confirm_counters.clear()

    def get_face_count(self):
        """获取已注册人脸数量"""
        with self._lock:
            return len(self.known_faces)

    def register_face_from_image(self, image_path):
        """从图片文件注册人脸

        Args:
            image_path: 图片路径

        Returns:
            encoding (numpy array) or None
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"无法读取图片: {image_path}")
                return None

            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            locations = self.detect_faces(rgb)

            if not locations:
                logger.warning(f"图片中未检测到人脸: {image_path}")
                return None

            # 使用最大的人脸
            if len(locations) > 1:
                areas = [(r - t) * (b - l) for t, r, b, l in locations]
                best_idx = np.argmax(areas)
                locations = [locations[best_idx]]

            encoding = self.encode_face(rgb, locations[0])
            return encoding
        except Exception as e:
            logger.error(f"从图片注册人脸失败: {e}")
            return None

    def register_face_from_camera(self, camera_index=0, max_attempts=30):
        """从摄像头实时捕获注册人脸

        Args:
            camera_index: 摄像头索引
            max_attempts: 最大尝试帧数

        Returns:
            encoding (numpy array) or None
        """
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logger.error(f"无法打开摄像头 {camera_index}")
            return None

        encoding = None
        attempt = 0

        try:
            while attempt < max_attempts:
                ret, frame = cap.read()
                if not ret:
                    attempt += 1
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                locations = self.detect_faces(rgb)

                if locations:
                    # 选择最大的人脸
                    if len(locations) > 1:
                        areas = [(r - t) * (b - l) for t, r, b, l in locations]
                        best_idx = np.argmax(areas)
                        locations = [locations[best_idx]]

                    encoding = self.encode_face(rgb, locations[0])
                    if encoding is not None:
                        break

                attempt += 1
                time.sleep(0.1)
        finally:
            cap.release()

        return encoding


class CameraManager:
    """摄像头管理器"""

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self._lock = threading.Lock()
        self.is_running = False
        self._frame = None

    def open(self, camera_index=None, width=None, height=None):
        """打开摄像头"""
        with self._lock:
            if self.cap and self.cap.isOpened():
                self.cap.release()

            if camera_index is not None:
                self.camera_index = camera_index

            self.cap = cv2.VideoCapture(self.camera_index)

            if not self.cap.isOpened():
                logger.error(f"无法打开摄像头 {self.camera_index}")
                return False

            if width:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            if height:
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

            self.is_running = True
            logger.info(f"摄像头 {self.camera_index} 已打开")
            return True

    def read(self):
        """读取一帧"""
        with self._lock:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self._frame = frame
                    return True, frame
            return False, None

    def get_latest_frame(self):
        """获取最新帧 (非阻塞)"""
        return self._frame

    def close(self):
        """关闭摄像头"""
        with self._lock:
            self.is_running = False
            if self.cap:
                self.cap.release()
                self.cap = None
            logger.info("摄像头已关闭")

    def is_opened(self):
        """检查摄像头是否打开"""
        return self.cap is not None and self.cap.isOpened()

    def list_cameras(self, max_test=5):
        """列出可用摄像头"""
        available = []
        for i in range(max_test):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
