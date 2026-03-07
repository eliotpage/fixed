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

Optional flags:
```bash
./start_server.sh --port 5001 --tile-dir /path/to/tiles --public
```

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

Optional flags:
```bash
./start_client.sh --port 5000 --uid <connection-id>
```

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
1. Start ngrok in another terminal: `ngrok http 5001`
2. Start server with: `./start_server.sh --public`
3. Share printed Connection ID
