#!/bin/bash
# Start POPMAP in SERVER mode

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

# Run in server mode
# Optional environment variables for email functionality:
#   export SECRET_KEY=your-secret-key
#   export MAIL_USERNAME=your-gmail@gmail.com
#   export MAIL_PASSWORD=your-app-password
export APP_MODE=server
python3 app.py --server
