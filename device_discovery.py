# -*- coding: utf-8 -*-
"""
设备发现服务 - 使用UDP广播实现局域网设备发现
"""
import socket
import json
import threading
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DeviceDiscovery:
    """设备发现服务"""

    BROADCAST_PORT = 9999
    DISCOVERY_INTERVAL = 2  # 广播间隔（秒）
    RESPONSE_TIMEOUT = 5  # 响应超时（秒）

    def __init__(self, device_name, device_id, api_port=5000):
        """
        初始化设备发现服务

        Args:
            device_name: 设备名称
            device_id: 设备ID（通常是MAC地址或UUID）
            api_port: API服务端口
        """
        self.device_name = device_name
        self.device_id = device_id
        self.api_port = api_port
        self.running = False
        self.broadcast_socket = None
        self.listen_socket = None

        # 获取本机IP
        self.local_ip = self._get_local_ip()

    def _get_local_ip(self):
        """获取本机局域网IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def start_broadcast(self):
        """启动广播服务（PC端使用）"""
        if self.running:
            return

        self.running = True

        def broadcast_thread():
            """广播线程"""
            try:
                self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

                while self.running:
                    try:
                        # 构建设备信息
                        device_info = {
                            "type": "device_announce",
                            "device_name": self.device_name,
                            "device_id": self.device_id,
                            "ip": self.local_ip,
                            "port": self.api_port,
                            "timestamp": datetime.now().isoformat(),
                            "status": "online"
                        }

                        message = json.dumps(device_info, ensure_ascii=False).encode('utf-8')

                        # 广播到局域网
                        self.broadcast_socket.sendto(
                            message,
                            ('<broadcast>', self.BROADCAST_PORT)
                        )

                        logger.debug(f"广播设备信息: {self.device_name} @ {self.local_ip}:{self.api_port}")
                        time.sleep(self.DISCOVERY_INTERVAL)

                    except Exception as e:
                        logger.error(f"广播出错: {e}")
                        time.sleep(self.DISCOVERY_INTERVAL)

            except Exception as e:
                logger.error(f"广播线程出错: {e}")
            finally:
                if self.broadcast_socket:
                    self.broadcast_socket.close()

        thread = threading.Thread(target=broadcast_thread, daemon=True)
        thread.start()
        logger.info(f"设备发现广播服务已启动: {self.device_name}")

    def stop_broadcast(self):
        """停止广播服务"""
        self.running = False
        if self.broadcast_socket:
            self.broadcast_socket.close()

    @staticmethod
    def discover_devices(timeout=RESPONSE_TIMEOUT):
        """
        搜索局域网内的设备（手机端使用）

        Args:
            timeout: 搜索超时时间（秒）

        Returns:
            list: 发现的设备列表
        """
        discovered_devices = []

        try:
            # 创建UDP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)

            # 绑定端口
            try:
                sock.bind(('', 0))
            except:
                pass

            # 发送搜索请求
            search_message = json.dumps({
                "type": "device_search",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False).encode('utf-8')

            sock.sendto(search_message, ('<broadcast>', DeviceDiscovery.BROADCAST_PORT))

            # 接收响应
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = json.loads(data.decode('utf-8'))

                    if message.get('type') == 'device_announce':
                        device_info = {
                            'name': message.get('device_name'),
                            'id': message.get('device_id'),
                            'ip': message.get('ip'),
                            'port': message.get('port'),
                            'status': message.get('status', 'online'),
                            'last_seen': message.get('timestamp')
                        }

                        # 避免重复添加
                        if not any(d['id'] == device_info['id'] for d in discovered_devices):
                            discovered_devices.append(device_info)
                            logger.info(f"发现设备: {device_info['name']} @ {device_info['ip']}:{device_info['port']}")

                except socket.timeout:
                    break
                except Exception as e:
                    logger.error(f"接收设备响应出错: {e}")

            sock.close()

        except Exception as e:
            logger.error(f"设备搜索失败: {e}")

        return discovered_devices

    @staticmethod
    def get_device_id():
        """获取设备唯一ID"""
        try:
            import uuid
            # 使用MAC地址生成设备ID
            mac = uuid.getnode()
            return f"{mac:012x}"
        except:
            import random
            return f"{random.randint(100000, 999999)}"


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)

    # 测试PC端广播
    device_id = DeviceDiscovery.get_device_id()
    discovery = DeviceDiscovery("测试设备", device_id)
    discovery.start_broadcast()

    print("广播服务已启动，按Ctrl+C停止...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        discovery.stop_broadcast()
        print("\n已停止")
