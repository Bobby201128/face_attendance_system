@echo off
REM Face Attendance System Startup Script (Conda Environment)

echo ============================================================
echo   Face Attendance System - Conda Environment Startup
echo ============================================================
echo.

REM Check if conda is available
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Conda not found!
    echo Please install Miniconda or Anaconda first.
    echo.
    pause
    exit /b 1
)

REM Activate conda environment
echo [1/2] Activating conda environment: face_attendance
call conda activate face_attendance
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to activate conda environment!
    echo.
    pause
    exit /b 1
)

REM Start system
echo [2/2] Starting face attendance system...
echo.
echo ============================================================
echo.
python main.py

REM If system exits, pause to see error message
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo   System exited with error code: %ERRORLEVEL%
    echo ============================================================
    echo.
    pause
)
