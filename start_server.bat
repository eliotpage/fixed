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
REM Optional for public accessibility (use ngrok for local PC):
REM   1. Install ngrok from https://ngrok.com/download
REM   2. In a separate terminal: ngrok http 5001
REM   3. Run server with: start_server.bat --public
REM Optional for explicit public URL override:
REM   set PUBLIC_SERVER_URL=http://<your-public-ip>:5001
REM Optional to customize connection ID signing (must match on clients):
REM   set POPMAP_CONNECTION_SECRET=shared-connection-secret
REM Optional to customize tile directory when using map-based routing:
REM   set TILE_DIR=C:\path\to\tiles
REM   (server tiles are also used by remote clients via /tiles proxy)
REM Optional startup flags:
REM   --port <server-port>
REM   --tile-dir C:\path\to\tiles
REM   --public                 (use ngrok tunnel for public access)
REM Server startup will print a generated Connection ID to share with clients.
set APP_MODE=server
%PYTHON_CMD% app.py --server %*
