@echo off
chcp 65001 >nul
echo ====================================
echo   Face Recognition Attendance System - Installation Script
echo ====================================
echo.

echo [1/3] Checking Python environment...
python --version
if %errorlevel% neq 0 (
    echo Error: Python not found, please install Python 3.8+ first
    pause
    exit /b 1
)

echo.
echo [2/3] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Tip: If dlib installation fails, please refer to the following steps:
    echo   1. Install CMake: pip install cmake
    echo   2. Install Visual Studio Build Tools
    echo   3. Or use precompiled dlib whl file
    echo.
    pause
)

echo.
echo [3/3] Installation completed!
echo.
echo How to start:
echo   python main.py
echo.
echo Mobile access:
echo   Enter computer IP:5000 in mobile browser
echo   Default password: admin123
echo.
pause
