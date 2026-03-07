@echo off
setlocal

cd /d "%~dp0"
cd app

set "WANTS_NGROK=0"
for %%A in (%*) do (
    if /I "%%~A"=="--ngrok" set "WANTS_NGROK=1"
)

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
pip install -q -r requirements.txt

set APP_MODE=server
%PYTHON_CMD% app.py --server %*
