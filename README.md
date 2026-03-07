# POPMAP

Simple setup and run guide.

## 1) Download

Option A (git/curl style):
```bash
git clone https://github.com/eliotpage/POPMAP_NEA.git
cd POPMAP_NEA
```

Option B (manual):
1. Download ZIP from GitHub
2. Extract it
3. Open terminal in the extracted folder

## 2) Start Server

Linux/macOS:
```bash
./start_server.sh
```

Windows:
```bat
start_server.bat
```

Quick help:
```bash
./start_server.sh --help
```

Auth setup during server startup:
1. Server setup now checks `app/.env` for auth variables.
2. Missing `SECRET_KEY` and `POPMAP_CONNECTION_SECRET` are generated automatically.
3. You are prompted for `MAIL_USERNAME` and `MAIL_PASSWORD` (optional, needed for OTP email).
4. Values are saved to `app/.env` for future runs.

Optional flags:
```bash
./start_server.sh --port 5001 --tile-dir /path/to/tiles --ngrok
```

Force auth reconfiguration:
```bash
./start_server.sh --setup-auth
```

First-time remote setup (recommended):
```bash
./start_server.sh --setup-auth --ngrok
```

`--setup-auth` behavior:
1. Forces server setup to re-prompt for auth variables
2. Regenerates or rewrites `SECRET_KEY` and `POPMAP_CONNECTION_SECRET`
3. Prompts again for `MAIL_USERNAME` and `MAIL_PASSWORD`
4. Saves updated values into `app/.env`

`--ngrok` behavior:
1. `start_server.sh` and `start_server.bat` check whether `ngrok` exists
2. If missing, setup attempts to install it automatically
3. The server then starts and creates the tunnel

What server prints:
1. `Connection URL`
2. `Connection ID` (UID)

Share the Connection ID with clients.

## 3) Start Client

Linux/macOS:
```bash
./start_client.sh --uid <connection-id>
```

Windows:
```bat
start_client.bat --uid <connection-id>
```

Quick help:
```bash
./start_client.sh --help
```

Optional flags:
```bash
./start_client.sh --port 5002 --uid <connection-id>
```

Recommended backup client port if `5000` is busy: `5002`.

Open in browser:
1. Client: `http://localhost:5000` (or your `--port`)
2. Server monitor: `http://localhost:5001/monitor` (or your `--port`)

## 4) Login Flow

1. Enter email on client login page
2. Receive OTP email
3. Enter OTP
4. Open `/map`

## 5) Tiles (How It Works)

1. Server stores/serves tiles (`--tile-dir` on server)
2. Client requests `/tiles/...` from its own app
3. If client has no local tile, client proxies that tile request to server automatically

So clients can run without local tile copies.

## 6) Public Access From Anywhere

If server is in Codespaces:
1. Start server normally
2. Use printed Connection ID on any client

If server is local PC and needs internet access:
1. Start server with: `./start_server.sh --ngrok`
2. Setup auto-installs ngrok when missing (requires package manager/admin permissions)
3. Share printed Connection ID

If auto-install fails:
1. Install ngrok manually from `https://ngrok.com/download`
2. Rerun server with `--ngrok`
