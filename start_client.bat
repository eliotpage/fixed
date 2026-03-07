@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"
cd app

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

set "PYTHON_CMD=py -3"
where py >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=python"

REM Check if .env exists
if not exist ".env" (
    echo [Client] No .env file found in app directory.
    echo [Client] The client needs environment configuration to connect.
    echo.
    echo Options:
    echo   1. Copy the .env file from your server to app\.env
    echo   2. Use Linux/macOS: Run ./start_client.sh -s for interactive setup
    echo   3. Copy app\.env.example to app\.env and edit manually
    echo.
    echo Press Ctrl+C to exit, or press any key to continue anyway...
    pause >nul
)

set "LOGS_VALUE=0"
set "LOOKING_FOR_LOGS_VALUE=0"
set "LOOKING_FOR_UID_VALUE=0"
set "LOOKING_FOR_PORT_VALUE=0"
set "FORWARD_ARGS="
for %%A in (%*) do (
    if !LOOKING_FOR_LOGS_VALUE! equ 1 (
        set "LOGS_VALUE=%%~A"
        set "LOOKING_FOR_LOGS_VALUE=0"
    ) else if !LOOKING_FOR_UID_VALUE! equ 1 (
        set "FORWARD_ARGS=!FORWARD_ARGS! --uid %%~A"
        set "LOOKING_FOR_UID_VALUE=0"
    ) else if !LOOKING_FOR_PORT_VALUE! equ 1 (
        set "FORWARD_ARGS=!FORWARD_ARGS! --port %%~A"
        set "LOOKING_FOR_PORT_VALUE=0"
    ) else if /I "%%~A"=="-l" (
        set "LOOKING_FOR_LOGS_VALUE=1"
    ) else if /I "%%~A"=="--logs" (
        set "LOOKING_FOR_LOGS_VALUE=1"
    ) else if /I "%%~A"=="-u" (
        set "LOOKING_FOR_UID_VALUE=1"
    ) else if /I "%%~A"=="--uid" (
        set "LOOKING_FOR_UID_VALUE=1"
    ) else if /I "%%~A"=="-p" (
        set "LOOKING_FOR_PORT_VALUE=1"
    ) else if /I "%%~A"=="--port" (
        set "LOOKING_FOR_PORT_VALUE=1"
    ) else (
        set "FORWARD_ARGS=!FORWARD_ARGS! %%~A"
    )
)

if not exist "venv\" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv venv
)

call venv\Scripts\activate.bat
set PIP_DISABLE_PIP_VERSION_CHECK=1
pip install -q -r requirements.txt

set APP_MODE=client

if !LOGS_VALUE! equ 1 (
    set QUIET_HTTP_LOGS=0
) else (
    set QUIET_HTTP_LOGS=1
)

%PYTHON_CMD% app.py !FORWARD_ARGS!
goto :eof

:help
echo POPMAP client launcher
echo Usage: start_client.bat -u ^<connection-id^> [options] [--port ^<port^>]
echo.
echo Options:
echo   -h, --help              Show this help message
echo   -u, --uid ^<id^>         Connection ID (required - share with server)
echo   -l, --logs ^<0^|1^>       0=quiet (default), 1=show HTTP request logs
echo   -p, --port ^<port^>      Port to run client on (default: 5000)
echo.
echo Examples:
echo   start_client.bat -u abc123def                    - Basic usage
echo   start_client.bat -u abc123def -l 1               - Show logs
echo   start_client.bat -u abc123def -p 5002            - Custom port
echo   start_client.bat -u abc123def -l 1 -p 5002       - Both options
exit /b 0
