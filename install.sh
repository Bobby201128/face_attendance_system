#!/bin/bash
# 人脸识别签到系统 - 安装脚本 (Linux/Mac)

echo "===================================="
echo "  人脸识别签到系统 - 安装脚本"
echo "===================================="
echo ""

echo "[1/3] 检查Python环境..."
python3 --version || python --version
if [ $? -ne 0 ]; then
    echo "错误: 未找到Python，请先安装Python 3.8+"
    exit 1
fi

echo ""
echo "[2/3] 安装依赖包..."
pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip install -r requirements.txt --break-system-packages 2>/dev/null

if [ $? -ne 0 ]; then
    echo ""
    echo "提示: 如果dlib安装失败，请参考以下步骤:"
    echo "  Ubuntu/Debian: sudo apt-get install cmake build-essential"
    echo "  macOS: xcode-select --install"
    echo ""
fi

echo ""
echo "[3/3] 安装完成!"
echo ""
echo "启动方式:"
echo "  python3 main.py"
echo ""
echo "手机端访问:"
echo "  在手机浏览器中输入电脑IP:5000"
echo "  默认密码: admin123"
echo ""
