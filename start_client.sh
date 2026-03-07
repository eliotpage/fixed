#!/bin/bash

cd "$(dirname "$0")"
cd app

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "POPMAP client launcher"
    echo "Usage: ./start_client.sh [--uid <connection-id>] [--port <client-port>]"
    exit 0
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

export PIP_DISABLE_PIP_VERSION_CHECK=1
pip install -q -r requirements.txt

export APP_MODE=client

python3 app.py "$@"
