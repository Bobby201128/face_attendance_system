# 人脸识别签到系统 (Face Attendance System)

## 项目简介

基于人脸识别技术的智能签到系统，支持 PC 端大屏显示和移动端 Web 管理。

## 核心功能

- 📷 **实时人脸检测和识别**
- ✅ **自动签到/签退**
- 💻 **PC 端全屏界面** - 实时摄像头画面和识别结果
- 📱 **移动端 Web 管理** - 人员管理、记录查询、数据导出
- 📊 **数据统计和报表** - 考勤统计、部门分析、Excel 导出

## 技术栈

- **人脸识别**: face_recognition + dlib
- **PC 界面**: PyQt5
- **Web 服务**: Flask
- **数据库**: SQLite
- **图像处理**: OpenCV

## 快速开始

### 1. 环境要求

- Python 3.9+
- Conda/Anaconda（推荐）
- 摄像头设备

### 2. 安装依赖

#### 使用 Conda（推荐）

```bash
# 创建并激活环境
conda create -n face_attendance python=3.9 -y
conda activate face_attendance

# 安装 dlib
conda install -c conda-forge dlib -y

# 安装 Python 依赖
pip install -r requirements.txt
```

#### 使用 pip（备选）

```bash
pip install -r requirements.txt
```

**注意**: 在 Windows 上直接安装 dlib 可能需要编译环境，建议使用 Conda。

### 3. 启动系统

#### 方法 1：使用启动脚本（Windows）
```bash
run_with_conda.bat
```

#### 方法 2：手动启动
```bash
# 激活环境
conda activate face_attendance

# 运行系统
python main.py
```

### 4. 访问管理界面

启动后会显示本机 IP 地址，例如：
```
本机IP: 192.168.1.100
手机端请访问: http://192.168.1.100:5000
默认密码: admin123
```

## 系统架构

```
face_attendance_system/
├── main.py                 # 主入口，协调 PC 端和 API 服务
├── pc_app.py              # PyQt5 桌面应用
├── api_server.py          # Flask API 服务器
├── face_engine.py         # 人脸识别引擎
├── database.py            # SQLite 数据库管理
├── video_threads.py       # 视频处理线程
├── config.py              # 配置文件
├── templates/             # Web 界面模板
├── data/                  # 数据存储（数据库、日志）
└── faces/                 # 人脸照片存储
```

## 配置说明

主要配置项在 `config.py` 中：

```python
# 人脸识别参数
RECOGNITION_MODE = "balanced"    # 识别模式
RECOGNITION_THRESHOLD = 0.55     # 识别阈值
CONFIRM_FRAMES = 3               # 确认帧数
SIGN_COOLDOWN = 60               # 签到冷却时间

# 工作时间
WORK_START_HOUR = 9
WORK_START_MINUTE = 0
LATE_GRACE_MINUTES = 15

# 网络服务
API_HOST = "0.0.0.0"
API_PORT = 5000
```

## 使用说明

### PC 端使用

1. 启动系统后会自动打开全屏界面
2. 点击"启动摄像头"开始识别
3. 可以切换"自动签到"和"手动签到"模式
4. 查看实时统计和签到记录

### 移动端使用

1. 在浏览器中访问显示的 IP 地址
2. 使用默认密码登录：`admin123`
3. 功能模块：
   - **首页**: 数据统计概览
   - **记录**: 签到记录查询和导出
   - **人员**: 人员管理和人脸注册
   - **统计**: 月度统计和部门分析
   - **监控**: 实时摄像头画面
   - **设置**: 系统配置和参数调整

## 常见问题

### Q: dlib 安装失败
**A**: 使用 Conda 安装：`conda install -c conda-forge dlib`

### Q: 摄像头无法打开
**A**: 检查 `config.py` 中的 `CAMERA_INDEX`，尝试不同的值（0, 1, 2...）

### Q: 人脸识别不准确
**A**: 调整 `config.py` 中的 `RECOGNITION_THRESHOLD`（0.5-0.7 之间）

### Q: 如何备份和恢复数据
**A**: 备份 `data/attendance.db` 文件即可

## 开发说明

详细的开发文档请查看 [CLAUDE.md](CLAUDE.md)

## 依赖项

见 [requirements.txt](requirements.txt)

## 许可证

本项目仅供学习和研究使用。

## 更新日志

- **v1.0** - 初始版本
  - 实现基础人脸识别签到功能
  - PC 端和移动端界面
  - 数据统计和导出功能

## 技术支持

如有问题，请查看：
- [QUICK_FIX_GUIDE.md](QUICK_FIX_GUIDE.md) - 快速修复指南
- [OPTIMIZATION_SUGGESTIONS.md](OPTIMIZATION_SUGGESTIONS.md) - 优化建议
- [SOLUTION_SUMMARY.md](SOLUTION_SUMMARY.md) - 解决方案总结
