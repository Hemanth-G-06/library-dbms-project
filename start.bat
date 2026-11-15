@echo off
title Smart Library Management System
echo ============================================================
echo   Smart Library Management System - Startup
echo ============================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo [*] Installing / checking dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [!] Warning: Some dependencies failed to install. Continuing...
)

echo.
echo [*] Launching Smart Library Application Server...
echo [*] Web app will open automatically in your browser at http://127.0.0.1:8000
echo.
python main.py
pause

