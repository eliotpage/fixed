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
# Optional for public accessibility (use ngrok for local PC):
#   1. Install ngrok: brew install ngrok (or download from ngrok.com)
#   2. In a separate terminal: ngrok http 5001
#   3. Run server with: ./start_server.sh --public
# Optional for explicit public URL override:
#   export PUBLIC_SERVER_URL=http://<your-public-ip>:5001
# Optional to customize connection ID signing (must match on clients):
#   export POPMAP_CONNECTION_SECRET=shared-connection-secret
# Optional to customize tile directory when using map-based routing:
#   export TILE_DIR=/path/to/tiles
#   (server tiles are also used by remote clients via /tiles proxy)
# Optional startup flags:
#   --port <server-port>
#   --tile-dir /path/to/tiles
#   --public                 (use ngrok tunnel for public access)
# Server startup will print a generated Connection ID to share with clients.
export APP_MODE=server

python3 app.py --server "$@"
