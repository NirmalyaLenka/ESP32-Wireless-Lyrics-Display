@echo off
echo.
echo  =============================================
echo   ESP32 Lyrics Bridge - Starting...
echo  =============================================
echo.

cd /d "%~dp0"

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found!
    echo  Please install Python from https://python.org
    pause
    exit /b
)

:: Install requirements if needed
echo  Installing required packages...
pip install -r requirements.txt --quiet

echo.
echo  Starting bridge server...
echo  Open http://localhost:5000/now-playing to test
echo  Press Ctrl+C to stop
echo.

python pc_bridge.py
pause
