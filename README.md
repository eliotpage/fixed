# POPMAP

Simple setup and run guide.

## Quick Start Overview

**Server Setup (First Time):**
1. Download and extract POPMAP
2. Run `start_server.sh` (or `.bat` on Windows)
3. If no `.env` exists, you'll be prompted to set it up automatically
4. Server generates secrets and saves to `app/.env`
5. Server prints Connection ID

**Client Setup (First Time):**
1. Download and extract POPMAP on client machine
2. Run `start_client.sh` (or `.bat` on Windows)
3. If no `.env` exists, you'll be prompted to set it up
4. Enter the SECRET_KEY and POPMAP_CONNECTION_SECRET from your server's `.env`
5. Run client with: `./start_client.sh --uid <connection-id>`
6. Open browser to `http://localhost:5000`

**Key Points:** 
- Both server and client will automatically detect missing `.env` and prompt for setup
- **Server** generates new secrets (use `-s` flag)
- **Client** asks you to enter secrets from the server's `.env` file (use `-s` flag)
- Both must have matching `SECRET_KEY` and `POPMAP_CONNECTION_SECRET` values

---

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

**First Time Setup:**

When you first download POPMAP, there's no `app/.env` file (excluded from git for security).

**Automatic Setup (Recommended):**

Just run the server - it will detect the missing `.env` and prompt you:

Linux/macOS:
```bash
./start_server.sh
```

Windows:
```bat
start_server.bat
```

When prompted, choose "Y" to set up automatically. The server will:
- Generate `SECRET_KEY` and `POPMAP_CONNECTION_SECRET` automatically
- Prompt for email settings (optional, for OTP authentication)
- Save everything to `app/.env`

**Manual Setup Alternative:**

Force setup mode:
```bash
./start_server.sh -s
```

Or copy the template manually:
```bash
cd app
cp .env.example .env
# Edit .env and generate secrets with: openssl rand -hex 32
```

**Starting the Server:**

Linux/macOS:
```bash
./start_server.sh
```

Windows:
```bat
start_server.bat
```
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

Common server usage:
```bash
# Start normally (quiet)
./start_server.sh

# Setup auth and ngrok (first time or reconfiguring)
./start_server.sh -s -n

# Show verbose HTTP logs
./start_server.sh -l 1

# Custom tile directory and port with verbose logs
./start_server.sh -t /path/to/tiles --port 5001 -l 1

# Full first-time setup with ngrok and logs
./start_server.sh -s -n -l 1
```

Server flag reference:

| Short | Long | Argument | Description |
|-------|------|----------|-------------|
| `-s` | `--setup-auth` | — | Forces re-prompt for auth secrets. Regenerates SECRET_KEY and POPMAP_CONNECTION_SECRET, re-prompts for MAIL_USERNAME/PASSWORD. |
| `-n` | `--ngrok` | — | Auto-installs ngrok (if missing) and creates tunnel for remote access. |
| `-l` | `--logs` | `0` or `1` | 0 = quiet (default), 1 = show HTTP request logs (verbose, for debugging). |
| `-t` | `--tile-dir` | `<path>` | Path to tile directory for map tiles. |
| `-h` | `--help` | — | Show help message with examples. |

What server prints:
1. `Connection URL`
2. `Connection ID` (UID)

**Important:** To connect clients to the server, you need to share TWO things:
1. The **Connection ID** (UID) - Share this openly
2. The **`app/.env` file** - This contains the secret needed to verify the Connection ID

## 3) Start Client

**Setting Up the Client:**

The client needs the same `.env` values as your server (specifically `SECRET_KEY` and `POPMAP_CONNECTION_SECRET`).

**Method 1: Interactive Setup (Recommended)**

Linux/macOS:
```bash
./start_client.sh -s
```

When prompted, enter the values from your server's `app/.env` file:
- `SECRET_KEY` (copy from server)
- `POPMAP_CONNECTION_SECRET` (copy from server) - **Must match exactly!**
- Email settings (optional)

**Method 2: Copy .env File from Server**

```bash
# Transfer the .env from server to client
scp user@server:/path/to/POPMAP/app/.env ./app/.env
```

**Method 3: Manual Copy**

1. Open `app/.env` on the server
2. Copy the contents
3. Create `app/.env` on the client and paste the contents

**Important Notes:**
- Copy the actual `.env` file, NOT `.env.example`
- The `POPMAP_CONNECTION_SECRET` must match exactly between server and client
- Without matching secrets, you'll get "invalid uid" errors

### Starting the client:

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

Common client usage:
```bash
# First time: setup .env with server's values
./start_client.sh -s

# Basic: connect with your connection ID
./start_client.sh -u abc123def

# Show verbose HTTP logs
./start_client.sh -u abc123def -l 1

# Use custom port (if 5000 is busy)
./start_client.sh -u abc123def -p 5002

# All options combined
./start_client.sh -u abc123def -l 1 -p 5002
```

Client flag reference:

| Short | Long | Argument | Description |
|-------|------|----------|-------------|
| `-s` | `--setup-env` | — | Interactive setup for .env file (enter values from server) |
| `-u` | `--uid` | `<id>` | Connection ID from server (required). Get this from server startup output. |
| `-l` | `--logs` | `0` or `1` | 0 = quiet (default), 1 = show HTTP request logs (verbose, for debugging). |
| `-p` | `--port` | `<port>` | Port to run client on. Default: 5000. Use 5002 if 5000 is busy. |
| `-h` | `--help` | — | Show help message with examples. |

**Note:** The client's `-s` flag prompts you to enter values (doesn't generate them). Enter the exact values from your server's `.env` file.

Open in browser:
1. Client: `http://localhost:5000` (or your `--port`)
2. Server monitor: `http://localhost:5001/monitor` (or your `--port`)

**Note:** If you get "invalid uid" errors, verify that the `app/.env` file on the client matches the server's `.env` file.

## 4) Login Flow

**Prerequisites:**
- Server running with valid email configuration (MAIL_USERNAME and MAIL_PASSWORD in `.env`)
- Client running with correct Connection ID and matching `.env` file

**Steps:**

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

**Setting up clients with matching .env:**
- Use `./start_client.sh -s` and enter the server's secret values, OR
- Copy the `app/.env` file directly from server to client

If server is in Codespaces:
1. Start server normally (auto-detects Codespaces URL)
2. Set up client `.env` with matching secrets
3. Use printed Connection ID on the client

If server is local PC and needs internet access:
1. Start server with: `./start_server.sh --ngrok`
2. Setup auto-installs ngrok when missing (requires package manager/admin permissions)
3. Set up client `.env` with matching secrets
4. Share printed Connection ID

If auto-install fails:
1. Install ngrok manually from `https://ngrok.com/download`
2. Rerun server with `--ngrok`

## 7) Troubleshooting

### No .env File After Fresh Download

**Problem:** After downloading/cloning POPMAP, there's no `app/.env` file.

**Cause:** The `.env` file is excluded from git for security (contains secrets).

**Solution:**
Simply run the startup script - it will detect the missing file and prompt you to set it up automatically:
- **Server:** `./start_server.sh` (generates secrets)
- **Client:** `./start_client.sh -s` (prompts for values from server)

Alternative: Copy the template manually:
```bash
cd app
cp .env.example .env
# Edit and fill in values
```

### "Invalid UID" Error on Client

**Problem:** Client shows "Invalid SERVER_ID" or "invalid uid" error when trying to connect.

**Cause:** The client's `POPMAP_CONNECTION_SECRET` doesn't match the server's.

**Solution:**
1. Check `app/.env` on both server and client
2. Verify `POPMAP_CONNECTION_SECRET` is **exactly the same** on both
3. If different, update client:
   - Run `./start_client.sh -s` and re-enter the correct value from server, OR
   - Copy the entire `.env` file from server to client
4. Restart the client

### Connection ID Expired

**Problem:** "Connection ID has expired" error.

**Solution:** Connection IDs are valid for 7 days by default. Get a new Connection ID by restarting the server.

### Port Already in Use

**Problem:** "Address already in use" error when starting server/client.

**Solution:**
- Server: Use `./start_server.sh --port 5002` (or any free port)
- Client: Use `./start_client.sh -u <uid> -p 5000` (if 5000 is free) or `-p 5002`

### Email/OTP Not Working

**Problem:** OTP emails not arriving.

**Solution:**
1. Check server logs for email errors
2. Verify `MAIL_USERNAME` and `MAIL_PASSWORD` in `app/.env` are correct
3. For Gmail: Use an App Password, not your regular password
4. Re-run server with `-s` flag to reconfigure email settings

## 8) Security Notes

- **`.env` file contains secrets:** Keep it secure, only share with trusted clients
- **Matching secrets required:** Server and all clients must have the same `POPMAP_CONNECTION_SECRET`
- **Two ways to set up client `.env`:**
  1. Use `./start_client.sh -s` and manually enter values from server (more secure - no file transfer needed)
  2. Copy the `.env` file from server (faster but requires secure file transfer)
- **Connection IDs expire:** Default 7 days. Get new ones by restarting the server
- **HTTPS recommended:** For production use, run behind HTTPS proxy or use ngrok
- **Email credentials:** Store securely, never commit `.env` to version control
- **`.env.example` is safe to commit:** It's just a template with no real secrets
