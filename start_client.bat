@echo off
setlocal

REM Start POPMAP in CLIENT mode
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

REM Nginx startup from Linux script is not applied on Windows.
set APP_MODE=client
REM Optional flags:
REM   --port <client-port>
REM   --uid <connection-id>  (alias: --server-id)
REM   --tile-dir C:\path\to\tiles   (optional local tile cache; otherwise tiles are proxied from server)
%PYTHON_CMD% app.py %*
