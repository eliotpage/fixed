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
# Optional for cross-device clients:
#   export PUBLIC_SERVER_URL=http://<your-lan-ip>:5001
# Optional to customize connection ID signing (must match on clients):
#   export POPMAP_CONNECTION_SECRET=shared-connection-secret
# Server startup will print a generated Connection ID to share with clients.
export APP_MODE=server
python3 app.py --server
