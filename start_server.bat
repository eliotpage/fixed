@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"
cd app

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

set "FORCE_AUTH_SETUP=0"
set "WANTS_NGROK=0"
set "LOGS_VALUE=0"
set "LOOKING_FOR_LOGS_VALUE=0"
set "LOOKING_FOR_TILE_VALUE=0"
set "FORWARD_ARGS="

for %%A in (%*) do (
    if !LOOKING_FOR_LOGS_VALUE! equ 1 (
        set "LOGS_VALUE=%%~A"
        set "LOOKING_FOR_LOGS_VALUE=0"
    ) else if !LOOKING_FOR_TILE_VALUE! equ 1 (
        set "FORWARD_ARGS=!FORWARD_ARGS! --tile-dir %%~A"
        set "LOOKING_FOR_TILE_VALUE=0"
    ) else if /I "%%~A"=="-s" (
        set "FORCE_AUTH_SETUP=1"
    ) else if /I "%%~A"=="--setup-auth" (
        set "FORCE_AUTH_SETUP=1"
    ) else if /I "%%~A"=="-n" (
        set "WANTS_NGROK=1"
        set "FORWARD_ARGS=!FORWARD_ARGS! --ngrok"
    ) else if /I "%%~A"=="--ngrok" (
        set "WANTS_NGROK=1"
        set "FORWARD_ARGS=!FORWARD_ARGS! --ngrok"
    ) else if /I "%%~A"=="-l" (
        set "LOOKING_FOR_LOGS_VALUE=1"
    ) else if /I "%%~A"=="--logs" (
        set "LOOKING_FOR_LOGS_VALUE=1"
    ) else if /I "%%~A"=="-t" (
        set "LOOKING_FOR_TILE_VALUE=1"
    ) else if /I "%%~A"=="--tile-dir" (
        set "LOOKING_FOR_TILE_VALUE=1"
    ) else (
        set "FORWARD_ARGS=!FORWARD_ARGS! %%~A"
    )
)

set "ENV_FILE=.env"

if not exist "%ENV_FILE%" (
    echo [Server] No .env file found in app directory.
    echo [Server] The server needs environment configuration.
    echo.
    echo Options:
    echo   1. Use Linux/macOS: Run ./start_server.sh -s for interactive setup
    echo   2. Copy app\.env.example to app\.env and edit manually
    echo   3. Press any key to create an empty .env ^(you'll need to configure it^)
    echo.
    pause
    type nul > "%ENV_FILE%"
)
)

set "SECRET_KEY_VALUE="
set "POPMAP_CONNECTION_SECRET_VALUE="
set "MAIL_USERNAME_VALUE="
set "MAIL_PASSWORD_VALUE="

for /f "usebackq tokens=1,* delims==" %%K in ("%ENV_FILE%") do (
    if /I "%%K"=="SECRET_KEY" set "SECRET_KEY_VALUE=%%L"
    if /I "%%K"=="POPMAP_CONNECTION_SECRET" set "POPMAP_CONNECTION_SECRET_VALUE=%%L"
    if /I "%%K"=="MAIL_USERNAME" set "MAIL_USERNAME_VALUE=%%L"
    if /I "%%K"=="MAIL_PASSWORD" set "MAIL_PASSWORD_VALUE=%%L"
)

if "%FORCE_AUTH_SETUP%"=="1" (
    echo [Setup] --setup-auth detected: forcing auth environment prompts.
    set "SECRET_KEY_VALUE="
    set "POPMAP_CONNECTION_SECRET_VALUE="
    set "MAIL_USERNAME_VALUE="
    set "MAIL_PASSWORD_VALUE="
)

if "%SECRET_KEY_VALUE%"=="" (
    for /f %%S in ('powershell -NoProfile -Command "[guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')"') do set "SECRET_KEY_VALUE=%%S"
    echo [Setup] SECRET_KEY missing. Generated one for app/.env.
)

if "%POPMAP_CONNECTION_SECRET_VALUE%"=="" (
    for /f %%S in ('powershell -NoProfile -Command "[guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')"') do set "POPMAP_CONNECTION_SECRET_VALUE=%%S"
    echo [Setup] POPMAP_CONNECTION_SECRET missing. Generated one for app/.env.
)

if "%MAIL_USERNAME_VALUE%"=="" (
    set /p MAIL_USERNAME_VALUE=[Setup] Enter MAIL_USERNAME (email for OTP), or leave blank to skip: 
)

if not "%MAIL_USERNAME_VALUE%"=="" if "%MAIL_PASSWORD_VALUE%"=="" (
    set /p MAIL_PASSWORD_VALUE=[Setup] Enter MAIL_PASSWORD (app password): 
)

set "TMP_ENV=.env.tmp"
if exist "%TMP_ENV%" del "%TMP_ENV%"

for /f "usebackq delims=" %%L in ("%ENV_FILE%") do (
    set "LINE=%%L"
    setlocal enabledelayedexpansion
    echo(!LINE!| findstr /b /i "SECRET_KEY= POPMAP_CONNECTION_SECRET= MAIL_USERNAME= MAIL_PASSWORD=" >nul
    if errorlevel 1 echo(!LINE!>> "%TMP_ENV%"
    endlocal
)

echo SECRET_KEY=%SECRET_KEY_VALUE%>> "%TMP_ENV%"
echo POPMAP_CONNECTION_SECRET=%POPMAP_CONNECTION_SECRET_VALUE%>> "%TMP_ENV%"
if not "%MAIL_USERNAME_VALUE%"=="" echo MAIL_USERNAME=%MAIL_USERNAME_VALUE%>> "%TMP_ENV%"
if not "%MAIL_PASSWORD_VALUE%"=="" echo MAIL_PASSWORD=%MAIL_PASSWORD_VALUE%>> "%TMP_ENV%"

move /y "%TMP_ENV%" "%ENV_FILE%" >nul

if "%WANTS_NGROK%"=="1" (
    where ngrok >nul 2>&1
    if errorlevel 1 (
        echo [Setup] --ngrok detected and ngrok is missing. Attempting install...

        where winget >nul 2>&1
        if not errorlevel 1 (
            winget install --id Ngrok.Ngrok -e --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
        )

        where ngrok >nul 2>&1
        if errorlevel 1 (
            where choco >nul 2>&1
            if not errorlevel 1 choco install ngrok -y >nul 2>&1
        )

        where ngrok >nul 2>&1
        if errorlevel 1 (
            where scoop >nul 2>&1
            if not errorlevel 1 scoop install ngrok >nul 2>&1
        )

        where ngrok >nul 2>&1
        if errorlevel 1 (
            echo [Setup] Could not auto-install ngrok.
            echo [Setup] Install ngrok from https://ngrok.com/download and rerun with --ngrok.
        ) else (
            echo [Setup] ngrok installed successfully.
        )
    )
)

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

set APP_MODE=server

if !LOGS_VALUE! equ 1 (
    set QUIET_HTTP_LOGS=0
) else (
    set QUIET_HTTP_LOGS=1
)

%PYTHON_CMD% app.py --server !FORWARD_ARGS!
goto :eof

:help
echo POPMAP server launcher
echo Usage: start_server.bat [options] [--port ^<port^>] [--tile-dir ^<path^>]
echo.
echo Options:
echo   -h, --help              Show this help message
echo   -s, --setup-auth        Force reconfiguration of auth secrets
echo   -n, --ngrok             Auto-install and setup ngrok tunnel
echo   -l, --logs ^<0^|1^>       0=quiet (default), 1=show HTTP request logs
echo   -t, --tile-dir ^<path^>   Path to tile directory
echo.
echo Examples:
echo   start_server.bat                        - Start normally (quiet)
echo   start_server.bat -s -n                  - Setup auth and ngrok
echo   start_server.bat -l 1                   - Show logs
echo   start_server.bat -s -n -l 1 --port 5001 - Full setup with verbose logs
exit /b 0
