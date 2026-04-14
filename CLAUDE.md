# CLAUDE.md

**交流语言：** 请在此仓库中使用**中文**进行所有交互。所有解释、注释和消息都应使用中文。

---

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 项目概述

这是一个人脸识别签到系统，同时具有桌面 PC 应用程序和移动端 Web 界面。系统执行实时人脸检测和识别，用于员工签到/签退。

**双界面架构：**
- **PC 端 (PyQt5)**：全屏桌面应用程序，具有实时摄像头画面、实时人脸识别、签到显示和管理界面
- **移动端**：移动端响应式 Web 界面，用于管理任务、监控和报告

## 常用开发命令

### 运行应用程序

```bash
# 安装依赖（仅首次）
pip install -r requirements.txt

# 运行完整系统（同时启动 PyQt5 PC 应用和 Flask API 服务器）
python main.py
```

系统将：
1. 在 `data/attendance.db` 初始化 SQLite 数据库
2. 加载已注册的人脸编码
3. 在 `0.0.0.0:5000` 启动 Flask API 服务器（后台线程）
4. 启动 PyQt5 桌面应用程序

通过 `http://<本地IP>:5000` 访问移动端界面，默认密码为 `admin123`。

### 开发测试

```bash
# 仅运行 API 服务器（用于 Web 界面测试）
python api_server.py

# 仅运行 PC 应用程序
python pc_app.py

# 直接测试数据库操作
python -c "from database import db; print(db.get_persons_with_encoding())"
```

## 架构概览

### 核心组件

```
main.py                 # 入口点 - 协调两个界面
├── api_server.py      # Flask REST API + Web UI（移动端界面）
├── pc_app.py          # PyQt5 桌面应用程序
├── face_engine.py     # 人脸检测/识别引擎
├── database.py        # SQLite 数据库操作
├── video_threads.py   # 视频捕获和识别的独立线程
├── config.py          # 集中式配置
└── templates/mobile.html  # 单页 Web 应用程序
```

### 线程架构

PC 应用程序采用**分离式线程模型**以获得最佳性能：

1. **VideoThread**（`video_threads.py`）：以全帧率从摄像头捕获帧，仅处理流畅显示
2. **RecognitionThread**：独立处理帧进行人脸检测/识别（约 15Hz），发出识别结果
3. **主线程**：处理 UI 更新、数据库操作，并协调线程之间的通信

这种分离防止了识别处理影响 UI 响应能力。

### 数据流

```
摄像头 → VideoThread → 帧缓冲区 → RecognitionThread → FaceEngine
                                                              ↓
                                                    识别结果
                                                              ↓
                                    主线程 (pc_app.py) → 数据库 + UI 更新
                                                              ↓
                                                    API 服务器（快照共享）
```

### 人脸识别流程

1. **检测**：使用 `face_recognition` 库（HOG 用于速度，CNN 可选用于精度）
2. **编码**：128 维人脸特征向量，以 pickle 格式的 numpy 数组存储在 SQLite 中
3. **匹配**：欧氏距离比较，具有可配置的阈值
4. **确认**：需要 N 个连续帧（默认为 3）来确认签到
5. **冷却**：防止在冷却期内重复签到（默认为 60 秒）

### 识别模式

在 `config.py` 中配置 `RECOGNITION_MODE`：
- `"fast"`：HOG 模型，无上采样，1 次抖动 - 适用于 <10 个人脸
- `"balanced"`：HOG 模型，1 倍上采样，2 次抖动 - 默认模式
- `"accurate"`：CNN 模型，1 倍上采样，3 次抖动 - 适用于 50+ 个人脸或光照不佳

## 配置

所有集中式设置在 `config.py` 中：

```python
# 识别敏感度（越高越严格，0.1-1.0）
RECOGNITION_THRESHOLD = 0.55  # 对于亚洲人脸，建议 0.55-0.60

# 确认要求
CONFIRM_FRAMES = 3      # 确认所需的连续帧数
SIGN_COOLDOWN = 60      # 同一人再次签到的间隔秒数

# 工作时间
WORK_START_HOUR = 9
WORK_START_MINUTE = 0
LATE_GRACE_MINUTES = 15

# API 服务器
API_HOST = "0.0.0.0"
API_PORT = 5000
```

运行时设置（可通过 Web 界面修改）存储在数据库 `settings` 表中，优先于 `config.py` 值。

## 数据库架构

```sql
persons          -- 员工记录，包含人脸编码（BLOB）
attendance       -- 签到/签退记录
settings         -- 系统配置（键值对）
operation_logs   -- 审计日志
```

关键表：
- `persons.face_encoding`：Pickle 格式的 128 维 numpy 数组
- `attendance`：链接到 `persons.id`，跟踪签到/签退及置信度分数
- 在 `attendance(person_id, sign_time)` 上建立索引以加快查询

## 人脸注册

有两种方法可用：

1. **通过 PC 应用程序**：添加人员对话框 → 摄像头拍照或照片上传 → 人脸检测 → 存储编码
2. **通过移动端 Web**：上传照片 → `/api/persons/{id}/face` 端点 → 服务器端编码

已注册的人脸存储为 `faces/{person_id}_{uuid}.jpg`，并在 `persons.face_image_path` 中引用。

## API 端点

大多数端点需要身份验证（来自 `/api/auth/login` 的 Bearer token）：

```
POST   /api/auth/login                   # 登录，返回 token
POST   /api/auth/change-password         # 修改管理员密码

GET    /api/persons                      # 列出人员（分页，可搜索）
POST   /api/persons                      # 添加人员
PUT    /api/persons/{id}                 # 更新人员
DELETE /api/persons/{id}                 # 删除人员（软删除）
POST   /api/persons/{id}/face            # 注册人脸（图片上传）

GET    /api/attendance/today             # 今日签到记录
GET    /api/attendance                   # 日期范围查询
POST   /api/attendance/manual            # 手动签到/签退

GET    /api/statistics/today             # 每日汇总
GET    /api/statistics/monthly           # 月度统计
GET    /api/statistics/departments       # 部门明细

GET    /api/monitor/snapshot             # 当前摄像头帧（base64）
GET    /api/monitor/status               # 系统状态（CPU、内存等）

GET    /api/settings                     # 获取配置
PUT    /api/settings                     # 更新配置

GET    /api/export/attendance            # Excel 导出
GET    /api/export/persons               # Excel 导出

GET    /                                # 移动端 Web 界面
```

## 开发说明

### 添加新的 API 端点

1. 在 `api_server.py` 中添加路由处理程序
2. 对受保护的端点应用 `@require_auth` 装饰器
3. 使用 `success_response()` / `error_response()` 辅助函数
4. 使用 `db.add_log()` 记录操作

### 修改识别参数

运行时可修改的参数：
- 识别阈值（通过 `face_engine.set_threshold()`）
- 确认帧数（通过 `face_engine.set_confirm_frames()`）
- 冷却时间（通过 `face_engine.set_cooldown()`）
- 识别模式（通过 `face_engine.set_mode()`）

通过 Web 界面（设置页面）或直接在 `FaceEngine` 实例上应用更改。

### 线程安全

- `FaceEngine` 对已知人脸列表使用线程锁
- 视频/识别线程通过 Qt 信号/槽通信
- 数据库使用上下文管理器确保事务安全

### 扩展 Web UI

移动端界面是 `templates/mobile.html` 中的单页应用程序。要修改：
1. 直接在模板中编辑 HTML/CSS
2. JavaScript 函数通过 `api()` 辅助函数进行 API 调用
3. 状态在全局变量中管理（TOKEN、API_BASE、currentPage）

### 调试

日志写入 `data/system.log`。在 `config.py` 中调整日志级别：

```python
LOG_LEVEL = "DEBUG"  # DEBUG, INFO, WARNING, ERROR
```

识别引擎在 DEBUG 级别记录详细的人脸检测事件。

## 故障排除

**常见问题：**

1. **误报/误识别**：提高 `RECOGNITION_THRESHOLD`（对于亚洲人脸，尝试 0.60-0.65）
2. **漏检**：降低阈值或切换到 "accurate" 模式
3. **UI 缓慢**：检查识别是否阻塞；确保线程正确分离
4. **摄像头无法打开**：验证配置中的 `CAMERA_INDEX` 与实际摄像头设备匹配
5. **数据库锁定**：已启用 SQLite WAL 模式；检查是否有长时间运行的事务
