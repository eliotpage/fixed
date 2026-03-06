@echo off
setlocal

REM Start POPMAP in SERVER mode
cd /d "%~dp0"
cd app

REM Choose Python launcher (prefer py, fallback to python)
set "PYTHON_CMD=py -3"
where py >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=python"

REM Create virtual environment if needed
if not exist "venv\" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv venv
)

REM Install/update dependencies
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

REM Optional environment variables for email functionality:
REM   set SECRET_KEY=your-secret-key
REM   set MAIL_USERNAME=your-gmail@gmail.com
REM   set MAIL_PASSWORD=your-app-password
REM Optional for cross-device clients:
REM   set PUBLIC_SERVER_URL=http://<your-lan-ip>:5001
REM Optional to customize connection ID signing (must match on clients):
REM   set POPMAP_CONNECTION_SECRET=shared-connection-secret
REM Server startup will print a generated Connection ID to share with clients.
set APP_MODE=server
%PYTHON_CMD% app.py --server
