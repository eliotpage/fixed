#!/bin/bash
# Start POPMAP in CLIENT mode

cd "$(dirname "$0")"
cd app

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -q -r requirements.txt

# Start/reload nginx as reverse proxy (best-effort)
if command -v nginx >/dev/null 2>&1; then
    echo "Starting nginx (proxy on port 80)..."
    sudo service nginx start >/dev/null 2>&1 || true
fi

# Run in client mode
export APP_MODE=client

# Optional flags:
#   --port <client-port>
#   --uid <connection-id>  (alias: --server-id)
#   --tile-dir /path/to/tiles   (optional local tile cache; otherwise tiles are proxied from server)
python3 app.py "$@"
