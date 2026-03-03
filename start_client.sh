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

# Run in client mode
export APP_MODE=client
python3 app.py
