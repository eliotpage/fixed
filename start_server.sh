#!/bin/bash

cd "$(dirname "$0")"
cd app

WANTS_NGROK=0
for arg in "$@"; do
    if [ "$arg" = "--ngrok" ]; then
        WANTS_NGROK=1
        break
    fi
done

ensure_ngrok() {
    if command -v ngrok >/dev/null 2>&1; then
        return 0
    fi

    echo "[Setup] --ngrok detected and ngrok is missing. Attempting install..."

    if command -v brew >/dev/null 2>&1; then
        brew install ngrok/ngrok/ngrok >/dev/null 2>&1 || brew install ngrok >/dev/null 2>&1
    elif command -v apt-get >/dev/null 2>&1; then
        if command -v sudo >/dev/null 2>&1; then
            sudo apt-get update >/dev/null 2>&1 && (sudo apt-get install -y ngrok >/dev/null 2>&1 || sudo apt-get install -y ngrok-client >/dev/null 2>&1)
        else
            apt-get update >/dev/null 2>&1 && (apt-get install -y ngrok >/dev/null 2>&1 || apt-get install -y ngrok-client >/dev/null 2>&1)
        fi
    fi

    if command -v ngrok >/dev/null 2>&1; then
        echo "[Setup] ngrok installed successfully."
        return 0
    fi

    echo "[Setup] Could not auto-install ngrok."
    echo "[Setup] Install ngrok manually from https://ngrok.com/download and rerun with --ngrok."
    return 1
}

if [ "$WANTS_NGROK" -eq 1 ]; then
    ensure_ngrok || true
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

pip install -q -r requirements.txt

export APP_MODE=server

python3 app.py --server "$@"
