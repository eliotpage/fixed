@echo off
setlocal

cd /d "%~dp0"
cd app

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

set "PYTHON_CMD=py -3"
where py >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=python"

if not exist "venv\" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv venv
)

call venv\Scripts\activate.bat
set PIP_DISABLE_PIP_VERSION_CHECK=1
pip install -q -r requirements.txt

set APP_MODE=client
%PYTHON_CMD% app.py %*
goto :eof

:help
echo POPMAP client launcher
echo Usage: start_client.bat [--uid ^<connection-id^>] [--port ^<client-port^>]
