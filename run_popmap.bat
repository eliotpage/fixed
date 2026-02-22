@echo off
REM POPMAP Launcher for Windows

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Check if venv exists, if not create it
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies if needed
python -c "import flask" 2>nul
if errorlevel 1 (
    echo 📚 Installing dependencies...
    pip install -q -r requirements.txt
)

REM Start Flask and open browser
echo 🚀 Starting POPMAP...
echo 📍 Access at: http://localhost:5000
echo 🛑 Press Ctrl+C to stop

REM Open browser
start http://localhost:5000

REM Run Flask
python app.py
pause
