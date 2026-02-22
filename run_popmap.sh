#!/bin/bash
# POPMAP Launcher for Linux/Mac

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if venv exists, if not create it
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import flask" 2>/dev/null; then
    echo "📚 Installing dependencies..."
    pip install -q -r requirements.txt
fi

# Start Flask and open browser
echo "🚀 Starting POPMAP..."
echo "📍 Access at: http://localhost:5000"
echo "🛑 Press Ctrl+C to stop"

# Open browser if possible
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:5000" 2>/dev/null &
elif command -v open &> /dev/null; then
    open "http://localhost:5000" 2>/dev/null &
fi

# Run Flask
python app.py
