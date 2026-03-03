# POPMAP - Point Of Presence Mapping & Analysis Platform

A unified tactical mapping application with pathfinding, hostile zone avoidance, and real-time collaboration features.

**POPMAP is now a unified application that runs in CLIENT or SERVER mode from the same codebase.**

---

## Quick Start

See [README_UNIFIED.md](README_UNIFIED.md) for complete documentation.

### Start CLIENT Mode (Default)
```bash
./start_client.sh              # Linux/macOS
# or
start_client.bat              # Windows
```

**Then open:** http://localhost:5000

### Start SERVER Mode
```bash
./start_server.sh              # Linux/macOS
# or  
start_server.bat              # Windows
```

**Then open:** http://localhost:5001 (or /monitor for dashboard)

---

## Prerequisites
- Python 3.8 or newer
- ~500MB disk space for map tiles and terrain data

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/eliotpage/POPMAP_NEA.git
   cd POPMAP_NEA
   ```

2. **Create a Python environment:**
   ```bash
   cd app
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate.bat
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment (`.env` in `app/` directory):**
   ```bash
   SECRET_KEY=your-secret-key-here
   SERVER_URL=http://localhost:5001
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

6. **Open in your browser:**
   - Local: `http://localhost`
   - Remote: `http://your-server.com`

7. **Login** with your email - you'll receive an OTP code to authenticate

---

## ⚠️ CRITICAL: Get Map Data From Administrator

The downloaded app does **NOT include** map tiles or terrain data (they're too large - ~500MB).

**You MUST request these files from your administrator before the app will work:**

1. **Map Tiles** (~391MB) - offline satellite/terrain maps
2. **DEM File** (output_be.tif, ~18MB) - elevation data for pathfinding

### Setting Up the Map Files

Once you have the files from your administrator:

1. **Extract tiles** to: `client/static/tiles/`
   ```
   tiles/
   ├── 10/
   ├── 11/
   ├── 12/
   └── ... (zoom levels 2-17)
   ```

2. **Place DEM** at: `client/static/output_be.tif`

### Verify Before Running

```bash
# Check tiles exist
ls client/static/tiles/
# Should show: 10  11  12  13  14  15  16  17  etc.

# Check DEM exists (should be ~18MB)
ls -lh client/static/output_be.tif
```

### Without These Files
❌ Maps won't display  
❌ Pathfinding won't work  
❌ App won't function properly

**Contact your POPMAP administrator to get these files.**

---

## Project Structure

This project is organized into two separate deployments:

### `/server` - Admin Server
Full-featured server with authentication and email capabilities.

**Key Features:**
- Manages OTP authentication
- Sends emails via configured SMTP
- Server-side cryptography
- API endpoints for client applications
- Runs on port 5001

[See Server Documentation](./server/README.md)

### `/client` - Standalone Client
Lightweight, downloadable client for end users that authenticates via the server.

**Key Features:**
- No email configuration needed
- No local cryptography setup
- All authentication delegated to server
- Same mapping and pathfinding features
- Runs on port 5000

[See Client Documentation](./client/README.md)

## 🛠️ For Developers & Administrators

### Running Locally (Testing Both Apps)

**Terminal 1 - Run the Server:**
```bash
cd server
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate.bat on Windows
pip install -r requirements.txt
python app.py  # Server runs on port 5001
```

**Terminal 2 - Run the Client:**
```bash
cd client
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate.bat on Windows
pip install -r requirements.txt
python app.py  # Client runs on port 5000
```

Then open `http://localhost:5000` in your browser.

### Production Deployment (with Nginx)

Both apps are configured to run on port 80 when deployed behind nginx as a reverse proxy.

See detailed nginx configuration in the section below.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                 NGINX (Port 80)                      │
│         (Reverse Proxy / Load Balancer)              │
└────────┬────────────────────────────────┬────────────┘
         │                                │
         ↓                                ↓
    ┌─────────────┐              ┌─────────────┐
    │   Server    │              │   Client    │
    │ (Port 80)   │              │ (Port 80)   │
    │ :5001 →     │              │ :5000 →     │
    │ Admin       │              │ Users       │
    └─────────────┘              └─────────────┘

User Browser → nginx:80 → Routes to Server or Client App
```

## Nginx Configuration

### Single Machine Setup (both apps on same host)

Create `/etc/nginx/sites-available/popmap.conf`:

```nginx
# Server (Admin)
upstream popmap_server {
    server localhost:5001;
}

# Client (Users)
upstream popmap_client {
    server localhost:5000;
}

server {
    listen 80 default_server;
    server_name _;

    # Route /admin to server
    location /admin {
        proxy_pass http://popmap_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Route everything else to client (/) 
    location / {
        proxy_pass http://popmap_client;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Separate Machines Setup

**Server Machine** (`/etc/nginx/sites-available/popmap-server.conf`):
```nginx
upstream popmap_server {
    server localhost:5001;
}

server {
    listen 80;
    server_name server.yourdomain.com;

    location / {
        proxy_pass http://popmap_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Client Machine** (`/etc/nginx/sites-available/popmap-client.conf`):
```nginx
upstream popmap_client {
    server localhost:5000;
}

server {
    listen 80;
    server_name client.yourdomain.com;

    location / {
        proxy_pass http://popmap_client;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Enable Nginx Config

```bash
sudo ln -s /etc/nginx/sites-available/popmap.conf /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### SSL/HTTPS (Recommended for Production)

Install Certbot:
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Certbot will automatically update your nginx config to use HTTPS on port 443 and redirect HTTP to HTTPS.

## Features

### 🗺️ Interactive Mapping
- Leaflet-based map with offline tile support
- Draw markers, lines, polygons, and circles
- Color-coded features with hostile zone marking
- Real-time drawing synchronization

### 🛣️ Intelligent Pathfinding
- D* Lite algorithm for optimal path calculation
- Hostile zone avoidance
- Terrain-aware routing using DEM data
- Risk assessment (Low/Medium/High)
- Corridor-based path constraints

### 🔒 Security
- OTP-based authentication via email
- Session management
- Server-side cryptography
- SHA-256 hashing for credentials

### 📊 Risk Analysis
- Automatic path risk calculation
- Proximity-based threat assessment
- Visual alerts for dangerous routes
- Distance metrics to hostile zones

## Deployment

### For Production Server
1. Configure `.env` with production email credentials
2. Set secure `SECRET_KEY`
3. Update CORS/network settings as needed
4. Deploy server to production server

### For Client Distribution
1. Package `/client` directory
2. Users configure `.env` with their server URL
3. Users install dependencies
4. Users run the application

## Requirements

- Python 3.8+
- Flask
- Rasterio (for DEM data)
- Leaflet.js (included)
- GDAL (for Rasterio)

## License

[Add your license here]

## Support

For issues or questions:
- Check server logs: `cd server && python app.py`
- Check client logs: `cd client && python app.py`
- Review `.env` configuration
- Verify server connectivity from client

