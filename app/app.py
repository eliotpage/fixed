import os
import json
import math
import threading
import time
import re
import sys
import argparse
import socket
import logging
import shutil
import subprocess
import atexit
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, Response
from lib.dstar import DStarLite
from lib.hashing import generate_otp, verify_otp, generate_connection_id, resolve_connection_id
from dotenv import load_dotenv
import numpy as np
import requests

parser = argparse.ArgumentParser(description='POPMAP Application')
parser.add_argument('--server', action='store_true', help='Run in server mode (default: client mode)')
parser.add_argument('--port', type=int, help='Port to bind this app to (default: 5000 client, 5001 server)')
parser.add_argument('--tile-dir', dest='tile_dir', type=str, help='Path to tile root directory (must contain zoom folders)')
parser.add_argument('--uid', type=str, help='Connection ID for client mode (alias for SERVER_ID)')
parser.add_argument('--server-id', dest='server_id', type=str, help='Connection ID for client mode (same as --uid)')
parser.add_argument('--ngrok', action='store_true', help='Start an ngrok tunnel automatically for remote connections (server mode only)')
args = parser.parse_args()

APP_MODE = os.getenv("APP_MODE", "server" if args.server else "client").lower()
if APP_MODE not in ["client", "server"]:
    APP_MODE = "client"

DEMO_DRAWINGS = [
    {"type": "Feature", "properties": {"_id": 1, "deleted": False, "color": "blue", "isMarker": True, "hostile": False},
     "geometry": {"type": "Point", "coordinates": [33.100, 35.100]}},
    {"type": "Feature", "properties": {"_id": 2, "deleted": True, "color": "red", "hostile": False},
     "geometry": {"type": "LineString", "coordinates": [[33.101, 35.101], [33.102, 35.102]]}},
    {"type": "Feature", "properties": {"_id": 3, "deleted": False, "color": "green", "hostile": False},
     "geometry": {"type": "Polygon", "coordinates": [[[33.103, 35.103], [33.104, 35.104], [33.105, 35.103], [33.103, 35.103]]]}}
]

DEMO_SHARED = [
    {"type": "Feature", "properties": {"_id": 2, "deleted": True, "color": "red", "hostile": False},
     "geometry": {"type": "LineString", "coordinates": [[33.101, 35.101], [33.102, 35.102]]}},
    {"type": "Feature", "properties": {"_id": 3, "deleted": True, "color": "green", "hostile": False},
     "geometry": {"type": "Polygon", "coordinates": [[[33.103, 35.103], [33.104, 35.104], [33.105, 35.103], [33.103, 35.103]]]}},
    {"type": "Feature", "properties": {"_id": 4, "deleted": False, "color": "orange", "isMarker": True, "hostile": False},
     "geometry": {"type": "Point", "coordinates": [33.106, 35.106]}}
]

DRAWINGS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'drawings.json')
SHARED_FILE = os.path.join(os.path.dirname(__file__), 'data', 'shared.json')
DEFAULT_TILE_DIR = os.path.join(os.path.dirname(__file__), 'static', 'tiles')
TILE_DIR = (args.tile_dir or os.getenv("TILE_DIR", DEFAULT_TILE_DIR)).strip() or DEFAULT_TILE_DIR
if not os.path.isabs(TILE_DIR):
    TILE_DIR = os.path.abspath(TILE_DIR)
if not os.path.isdir(TILE_DIR):
    print(f"[Startup] TILE_DIR not found: {TILE_DIR}")
    print("[Startup] Continuing without tile-based cost map; monitor and non-map features remain available.")
    TILE_DIR = None
DEM_PATH = os.path.join(os.path.dirname(__file__), 'static', 'output_be.tif')
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
MERGE_INTERVAL = 10

app = Flask(__name__, static_folder='static', static_url_path='/static')
load_dotenv()

LEAFLET_DRAW_DIST_DIR = os.path.join(os.path.dirname(__file__), 'static', 'leaflet-draw', 'dist')
LEAFLET_DRAW_SRC_DIR = os.path.join(os.path.dirname(__file__), 'static', 'leaflet-draw', 'src')

LEAFLET_DRAW_SRC_FILES = [
    'Leaflet.draw.js',
    'Leaflet.Draw.Event.js',
    'ext/TouchEvents.js',
    'ext/LatLngUtil.js',
    'ext/GeometryUtil.js',
    'ext/LineUtil.Intersect.js',
    'ext/Polyline.Intersect.js',
    'ext/Polygon.Intersect.js',
    'draw/handler/Draw.Feature.js',
    'draw/handler/Draw.Polyline.js',
    'draw/handler/Draw.Polygon.js',
    'draw/handler/Draw.SimpleShape.js',
    'draw/handler/Draw.Rectangle.js',
    'draw/handler/Draw.Marker.js',
    'draw/handler/Draw.CircleMarker.js',
    'draw/handler/Draw.Circle.js',
    'edit/handler/Edit.Marker.js',
    'edit/handler/Edit.Poly.js',
    'edit/handler/Edit.SimpleShape.js',
    'edit/handler/Edit.Rectangle.js',
    'edit/handler/Edit.CircleMarker.js',
    'edit/handler/Edit.Circle.js',
    'Control.Draw.js',
    'Toolbar.js',
    'Tooltip.js',
    'draw/DrawToolbar.js',
    'edit/EditToolbar.js',
    'edit/handler/EditToolbar.Edit.js',
    'edit/handler/EditToolbar.Delete.js',
]

os.makedirs(LOGS_DIR, exist_ok=True)


def log_action(action, result, details="", user_override=None):
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    ip_part = forwarded_for.split(',')[0].strip() if forwarded_for else None
    ip_addr = ip_part or request.remote_addr

    user_val = user_override or request.headers.get('X-User') or session.get('user') or session.get('email') or 'anonymous'

    log_entry = (
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} | "
        f"ip={ip_addr} "
        f"method={request.method} "
        f"path={request.path} "
        f"user={user_val} "
        f"action={action} "
        f"result={result} "
        f"details={details}"
    )
    try:
        with open(os.path.join(LOGS_DIR, 'actions.log'), 'a') as f:
            f.write(log_entry + '\n')
    except Exception as e:
        print(f"Error logging action: {e}")

if APP_MODE == "server":
    try:
        from flask_mail import Mail, Message
        
        app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        MAIL_USERNAME = os.getenv("MAIL_USERNAME")
        MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
        
        if MAIL_USERNAME and MAIL_PASSWORD:
            app.config.update(
                MAIL_SERVER='smtp.gmail.com',
                MAIL_PORT=587,
                MAIL_USE_TLS=True,
                MAIL_USERNAME=MAIL_USERNAME,
                MAIL_PASSWORD=MAIL_PASSWORD
            )
            mail = Mail(app)
            print("[Server] Email authentication enabled")
        else:
            mail = None
            print("[Server] Email not configured. Authentication endpoints will not send emails.")
            print("        Set MAIL_USERNAME and MAIL_PASSWORD environment variables to enable email.")
        
    except ImportError:
        print("Warning: flask_mail not installed. Email functionality will not work in server mode.")
        mail = None
else:
    app.secret_key = os.getenv("SECRET_KEY", "client-secret-key-change-in-production")
    mail = None

DEFAULT_SERVER_URL = "http://localhost:5001"
SERVER_URL = os.getenv("SERVER_URL", DEFAULT_SERVER_URL).strip() or DEFAULT_SERVER_URL
CONNECTION_ID_SECRET = os.getenv("POPMAP_CONNECTION_SECRET", "")
NGROK_PROCESS = None


def format_upstream_error(response, fallback_label="Server error"):
    """Normalize upstream API errors into user-friendly messages."""
    status = response.status_code
    try:
        result = response.json()
        base_error = result.get('error') or result.get('message')
    except Exception:
        base_error = None

    if status == 401 and "app.github.dev" in SERVER_URL:
        return (
            "Authentication server blocked request (401). "
            "In Codespaces, set port 5001 visibility to Public, then restart server and use a new Connection ID."
        )

    return base_error or f"{fallback_label} ({status})"

cli_connection_id = (args.uid or args.server_id or "").strip()

if cli_connection_id and APP_MODE == "server":
    print("[Startup] Ignoring --uid/--server-id in server mode (these are client-only flags).")

if args.ngrok and APP_MODE == "client":
    print("[Startup] Ignoring --ngrok in client mode (server-only flag).")

if APP_MODE == "client":
    server_id = cli_connection_id or os.getenv("SERVER_ID", "").strip()
    
    if not server_id:
        print("\n" + "="*60)
        print("POPMAP Client - Server Connection Required")
        print("="*60)
        print("\nNo Connection ID found. Please provide the Server's Connection ID.")
        print("You can get this from the server startup output.")
        print()
        try:
            server_id = input("Enter Connection ID (or press Enter for localhost:5001): ").strip()
        except EOFError:
            print("\n[Client] Non-interactive mode detected. Using localhost:5001")
            print("[Client] To connect to a remote server, use --uid flag or SERVER_ID env var.")
            server_id = None
    
    if server_id:
        try:
            SERVER_URL = resolve_connection_id(server_id, CONNECTION_ID_SECRET or None)
            print(f"[Client] Resolved server from SERVER_ID: {SERVER_URL}")
        except ValueError as e:
            print(f"[Client] Invalid SERVER_ID: {e}")
            print("[Client] Startup aborted. Enter a valid Connection ID.")
            sys.exit(1)
    elif SERVER_URL in ("http://localhost", "https://localhost"):
        SERVER_URL = f"{SERVER_URL}:5001"
        print(f"[Client] Using default server at {SERVER_URL}")
        print(f"[Client] To connect to a remote server, restart with --uid <CONNECTION_ID>")


def detect_public_url(port, use_ngrok=False):
    """Detect server's public URL for Connection IDs.
    
    Precedence:
    1. PUBLIC_SERVER_URL environment variable (explicit override)
    2. GitHub Codespaces public URL (auto-detected)
    3. ngrok tunnel (if --ngrok flag set)
    4. Local IP (for same-network connections)
    """
    explicit_url = os.getenv("PUBLIC_SERVER_URL", "").strip()
    if explicit_url:
        return explicit_url
    
    if os.getenv("CODESPACES") == "true":
        codespace_name = os.getenv("CODESPACE_NAME", "").strip()
        codespaces_domain = os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "preview.app.github.dev").strip()
        if codespace_name:
            return f"https://{codespace_name}-{port}.{codespaces_domain}"
    
    if use_ngrok:
        ngrok_url = detect_ngrok_tunnel()
        if ngrok_url:
            return ngrok_url
    
    return f"http://{detect_local_ip()}:{port}"


def detect_ngrok_tunnel(quiet=False):
    """Try to get ngrok tunnel URL from ngrok API (assumes ngrok is running).
    
    ngrok typically exposes its API on http://127.0.0.1:4040 by default.
    """
    import json
    import urllib.request

    api_candidates = []
    env_api = os.getenv("NGROK_API_URL", "").strip()
    if env_api:
        api_candidates.append(env_api)
    api_candidates.extend([
        'http://127.0.0.1:4040/api/tunnels',
        'http://127.0.0.1:4041/api/tunnels',
    ])

    for api_url in api_candidates:
        try:
            with urllib.request.urlopen(api_url, timeout=2) as res:
                data = json.loads(res.read().decode())
                tunnels = data.get('tunnels', [])

                for tunnel in tunnels:
                    if tunnel.get('proto') in ('http', 'https'):
                        public_url = tunnel.get('public_url')
                        if public_url:
                            print(f"[Server] Detected ngrok tunnel: {public_url}")
                            return public_url
        except Exception:
            continue

    if not quiet:
        print("[Server] ngrok tunnel URL not detected from local API.")
        print("[Server] If needed, set NGROK_API_URL or run `ngrok config add-authtoken <token>`.")
        print("[Server] Fallback to local IP detection.")
    
    return None


def stop_ngrok_tunnel():
    """Terminate ngrok process if this app started it."""
    global NGROK_PROCESS
    if NGROK_PROCESS and NGROK_PROCESS.poll() is None:
        try:
            NGROK_PROCESS.terminate()
            NGROK_PROCESS.wait(timeout=3)
            print("[Server] Stopped ngrok tunnel process")
        except Exception:
            try:
                NGROK_PROCESS.kill()
            except Exception:
                pass
    NGROK_PROCESS = None


def start_ngrok_tunnel(port, timeout_seconds=20):
    """Start ngrok tunnel for the given port and return tunnel URL if available."""
    global NGROK_PROCESS

    existing_url = detect_ngrok_tunnel(quiet=True)
    if existing_url:
        return existing_url

    ngrok_bin = shutil.which("ngrok")
    if not ngrok_bin:
        print("[Server] ngrok executable not found on PATH. Install ngrok to use --ngrok.")
        return None

    cmd = [ngrok_bin, "http", str(port)]
    print(f"[Server] Starting ngrok tunnel: {' '.join(cmd)}")

    try:
        if os.getenv("VERBOSE_LOGGING"):
            NGROK_PROCESS = subprocess.Popen(cmd)
        else:
            NGROK_PROCESS = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[Server] Failed to launch ngrok: {e}")
        NGROK_PROCESS = None
        return None

    atexit.register(stop_ngrok_tunnel)

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        url = detect_ngrok_tunnel(quiet=True)
        if url:
            return url
        time.sleep(0.5)

    print("[Server] ngrok started but tunnel URL was not detected in time.")
    return None


def detect_local_ip():
    """Best-effort local IP detection for connection ID generation."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        sock.close()

dstar = DStarLite(DEM_PATH, tile_dir=TILE_DIR, zoom=11)

if APP_MODE == "server":
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    @app.before_request
    def log_request():
        if request.path.startswith('/monitor'):
            return
        request.start_time = time.time()

    @app.after_request
    def log_response(response):
        if request.path.startswith('/monitor'):
            return response

        if hasattr(request, 'start_time'):
            duration_ms = (time.time() - request.start_time) * 1000
            qs = request.query_string.decode('utf-8') if request.query_string else '-'
            ref = (request.referrer or '-').replace(' ', '')
            ua = request.user_agent.string.replace('"', '')[:120]
            body_bytes = request.content_length or (response.calculate_content_length() or 0)

            forwarded_for = request.headers.get('X-Forwarded-For', '')
            ip_part = forwarded_for.split(',')[0].strip() if forwarded_for else None
            ip_addr = ip_part or request.remote_addr

            log_entry = (
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} | "
                f"ip={ip_addr} "
                f"method={request.method} "
                f"path={request.path} "
                f"qs=\"{qs or '-'}\" "
                f"status={response.status_code} "
                f"duration_ms={duration_ms:.2f} "
                f"bytes={body_bytes} "
                f"ref=\"{ref}\" "
                f"ua=\"{ua}\""
            )
            try:
                with open(os.path.join(LOGS_DIR, 'traffic.log'), 'a') as f:
                    f.write(log_entry + '\n')
            except Exception as e:
                print(f"Error logging traffic: {e}")
        return response

    def merge_drawings_loop():
        while True:
            if not os.path.exists(DRAWINGS_FILE) or not os.path.exists(SHARED_FILE):
                time.sleep(MERGE_INTERVAL)
                continue

            try:
                with open(DRAWINGS_FILE, 'r') as f:
                    drawings = json.load(f)
                with open(SHARED_FILE, 'r') as f:
                    shared = json.load(f)

                def build_dict(features):
                    d = {}
                    for f in features:
                        pid = f.get('properties', {}).get('_id')
                        if pid is not None:
                            d[pid] = f
                    return d

                drawings_dict = build_dict(drawings)
                shared_dict = build_dict(shared)
                merged_dict = {}

                all_ids = set(drawings_dict.keys()) | set(shared_dict.keys())
                for _id in all_ids:
                    d_feat = drawings_dict.get(_id)
                    s_feat = shared_dict.get(_id)

                    if d_feat and s_feat and d_feat['properties'].get('deleted') and s_feat['properties'].get('deleted'):
                        continue

                    if d_feat and not s_feat:
                        merged_dict[_id] = d_feat
                        continue
                    if s_feat and not d_feat:
                        merged_dict[_id] = s_feat
                        continue

                    merged = d_feat.copy()
                    merged_props = merged.get('properties', {}).copy()
                    merged_props['deleted'] = d_feat['properties'].get('deleted', False) or s_feat['properties'].get('deleted', False)
                    merged_props['hostile'] = d_feat['properties'].get('hostile', False) or s_feat['properties'].get('hostile', False)
                    merged_props['color'] = s_feat['properties'].get('color', d_feat['properties'].get('color', 'blue'))
                    merged['properties'] = merged_props
                    merged_dict[_id] = merged

                merged_list = list(merged_dict.values())

                with open(DRAWINGS_FILE, 'w') as f:
                    json.dump(merged_list, f, indent=2)
            except Exception as e:
                pass

            time.sleep(MERGE_INTERVAL)

    merge_thread = threading.Thread(target=merge_drawings_loop, daemon=True)

@app.route('/')
def index():
    if APP_MODE == "server":
        return render_template('monitor.html')
    else:
        return render_template('login.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/map')
def map_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/leaflet-draw/local/leaflet.draw.css')
def leaflet_draw_css_local():
    """Serve local Leaflet Draw CSS; fallback to src CSS when dist file is missing."""
    dist_css = os.path.join(LEAFLET_DRAW_DIST_DIR, 'leaflet.draw.css')
    if os.path.exists(dist_css):
        return send_from_directory(LEAFLET_DRAW_DIST_DIR, 'leaflet.draw.css', mimetype='text/css')

    src_css = os.path.join(LEAFLET_DRAW_SRC_DIR, 'leaflet.draw.css')
    if not os.path.exists(src_css):
        return Response('/* Leaflet Draw CSS missing */', status=404, mimetype='text/css')

    with open(src_css, 'r', encoding='utf-8') as f:
        css = f.read()

    css = css.replace("url('images/", "url('/leaflet-draw/local/images/")
    css = css.replace('url("images/', 'url("/leaflet-draw/local/images/')
    css = css.replace('url(images/', 'url(/leaflet-draw/local/images/')

    return Response(css, mimetype='text/css')


@app.route('/leaflet-draw/local/images/<path:filename>')
def leaflet_draw_images_local(filename):
    """Serve Leaflet Draw image assets from dist first, then src fallback."""
    dist_path = os.path.join(LEAFLET_DRAW_DIST_DIR, 'images', filename)
    src_path = os.path.join(LEAFLET_DRAW_SRC_DIR, 'images', filename)

    if os.path.exists(dist_path):
        return send_from_directory(os.path.join(LEAFLET_DRAW_DIST_DIR, 'images'), filename)
    if os.path.exists(src_path):
        return send_from_directory(os.path.join(LEAFLET_DRAW_SRC_DIR, 'images'), filename)

    if os.getenv('VERBOSE_LOGGING'):
        print(f"[Leaflet Draw] Image missing: {filename}")
    return Response(status=404)


@app.route('/leaflet-draw/local/leaflet.draw.js')
def leaflet_draw_js_local():
    """Serve local Leaflet Draw JS; fallback to concatenated src files when dist file is missing."""
    dist_js = os.path.join(LEAFLET_DRAW_DIST_DIR, 'leaflet.draw.js')
    if os.path.exists(dist_js):
        return send_from_directory(LEAFLET_DRAW_DIST_DIR, 'leaflet.draw.js', mimetype='application/javascript')

    chunks = []
    missing = []
    for rel_path in LEAFLET_DRAW_SRC_FILES:
        src_path = os.path.join(LEAFLET_DRAW_SRC_DIR, rel_path)
        if not os.path.exists(src_path):
            missing.append(rel_path)
            continue
        with open(src_path, 'r', encoding='utf-8') as f:
            chunks.append(f"\n/* --- {rel_path} --- */\n" + f.read())

    if missing:
        return Response(
            '/* Missing Leaflet Draw source files: ' + ', '.join(missing) + ' */',
            status=404,
            mimetype='application/javascript'
        )

    return Response('\n'.join(chunks), mimetype='application/javascript')


@app.route('/tiles/<int:z>/<int:x>/<int:y>.png')
def tile_file(z, x, y):
    """Serve tiles locally when present, otherwise proxy from server in client mode."""
    MAX_NATIVE_ZOOM = 15
    
    if z > MAX_NATIVE_ZOOM:
        scale_factor = 2 ** (z - MAX_NATIVE_ZOOM)
        z_native = MAX_NATIVE_ZOOM
        x_native = x // scale_factor
        y_native = y // scale_factor
        z, x, y = z_native, x_native, y_native
    
    tile_name = f"{y}.png"

    if TILE_DIR:
        tile_folder = os.path.join(TILE_DIR, str(z), str(x))
        local_tile = os.path.join(tile_folder, tile_name)
        if os.path.exists(local_tile):
            return send_from_directory(tile_folder, tile_name)

    if APP_MODE == "client":
        target = f"{SERVER_URL.rstrip('/')}/tiles/{z}/{x}/{y}.png"
        try:
            upstream = requests.get(target, timeout=10)
            if upstream.status_code == 200:
                response = Response(upstream.content, mimetype=upstream.headers.get("Content-Type", "image/png"))
                response.headers["Cache-Control"] = upstream.headers.get("Cache-Control", "public, max-age=3600")
                return response
            if upstream.status_code == 404:
                return Response(status=404)
            return Response(status=502)
        except Exception as e:
            print(f"[Tile Proxy Error] target={target} error={e}")
            return Response(status=502)

    if os.getenv("VERBOSE_LOGGING"):
        print(f"[Tile Not Found] z={z} x={x} y={y} - tile file does not exist")
    return Response(status=404)


@app.route('/request_otp', methods=['POST'])
def request_otp():
    data = request.get_json()
    user = data.get('user')
    if not user:
        return jsonify(success=False, error="Missing email")
    
    if APP_MODE == "client":
        try:
            response = requests.post(f"{SERVER_URL}/send_otp", json={"user": user}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return jsonify(success=result.get('success', False), error=result.get('error', ''))
            else:
                return jsonify(success=False, error="Server error")
        except Exception as e:
            return jsonify(success=False, error="Could not reach authentication server")
    else:
        if not mail:
            return jsonify(success=False, error="Email not configured")
        
        token = generate_otp(app.secret_key, user)
        try:
            msg = Message(
                subject="POPMAP OTP Code",
                sender=MAIL_USERNAME,
                recipients=[user]
            )
            msg.body = f"Your POPMAP OTP code is: {token}\nThis code expires in 5 minutes."
            mail.send(msg)
            return jsonify(success=True)
        except Exception as e:
            return jsonify(success=False, error="Failed to send email")

@app.route('/login_verify', methods=['POST'])
def login_verify():
    data = request.get_json()
    user = data.get('user')
    token = data.get('otp')
    if not user or not token:
        return jsonify(success=False, error="Missing data")
    
    if APP_MODE == "client":
        try:
            response = requests.post(f"{SERVER_URL}/verify_otp", json={"user": user, "otp": token}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    session['user'] = user
                    return jsonify(success=True)
                else:
                    return jsonify(success=False, error=result.get('error', 'Invalid OTP'))
            else:
                upstream_error = format_upstream_error(response, "Server error")
                return jsonify(success=False, error=upstream_error)
        except Exception as e:
            return jsonify(success=False, error="Could not reach authentication server")
    else:
        if verify_otp(app.secret_key, user, token):
            session['user'] = user
            return jsonify(success=True)
        return jsonify(success=False, error="Invalid or expired OTP")

@app.route('/send_otp', methods=['POST'])
def send_otp():
    """Client API: Send OTP email to user"""
    if APP_MODE != "server":
        return jsonify(success=False, error="Not available in client mode"), 400
    
    if not mail:
        return jsonify(success=False, error="Email not configured"), 500
    
    data = request.get_json()
    user = data.get('user')
    if not user:
        log_action('send_otp', 'error', 'missing email')
        return jsonify(success=False, error="Missing email")
    
    token = generate_otp(app.secret_key, user)
    try:
        msg = Message(
            subject="POPMAP OTP Code",
            sender=MAIL_USERNAME,
            recipients=[user]
        )
        msg.body = f"Your POPMAP OTP code is: {token}\nThis code expires in 5 minutes."
        mail.send(msg)
        log_action('send_otp', 'ok', f'user={user}')
        return jsonify(success=True)
    except Exception as e:
        log_action('send_otp', 'error', f'user={user} error={str(e)[:50]}')
        return jsonify(success=False, error="Failed to send OTP")

@app.route('/verify_otp', methods=['POST'])
def verify_otp_endpoint():
    """Client API: Verify OTP sent by client"""
    if APP_MODE != "server":
        return jsonify(success=False, error="Not available in client mode"), 400
    
    data = request.get_json()
    user = data.get('user')
    token = data.get('otp')
    if not user or not token:
        log_action('verify_otp', 'error', 'missing data')
        return jsonify(success=False, error="Missing data")
    
    if verify_otp(app.secret_key, user, token):
        log_action('verify_otp', 'ok', f'user={user}')
        return jsonify(success=True)
    log_action('verify_otp', 'error', f'user={user} invalid_token')
    return jsonify(success=False, error="Invalid or expired OTP")

@app.route('/action/log', methods=['POST'])
def action_log():
    """Capture user draw/delete actions; in client mode, forward to server if configured."""
    payload = request.get_json(force=True, silent=True) or {}

    action = payload.get('action', 'unknown')
    result = payload.get('result', 'ok')
    feature_id = payload.get('feature_id')
    geometry = payload.get('geometry')
    color = payload.get('color')
    hostile = payload.get('hostile')
    deleted = payload.get('deleted')

    parts = []
    if feature_id is not None:
        parts.append(f"id={feature_id}")
    if geometry:
        parts.append(f"type={geometry}")
    if color:
        parts.append(f"color={color}")
    if hostile is not None:
        parts.append(f"hostile={hostile}")
    if deleted is not None:
        parts.append(f"deleted={deleted}")

    detail_str = f"event={action} " + " ".join(parts)
    user_override = payload.get('user')

    if APP_MODE == "client":
        try:
            target = f"{SERVER_URL.rstrip('/')}/action/log"
            resp = requests.post(
                target,
                json=payload,
                headers={
                    "X-Forwarded-For": request.remote_addr,
                    "X-User": user_override or ''
                },
                timeout=2
            )
            if resp.ok:
                return jsonify(success=True, forwarded=True)
            else:
                log_action('action_log_forward', 'error', f"status={resp.status_code}")
        except Exception as e:
            log_action('action_log_forward', 'error', f"message={str(e)[:80]}")

    try:
        log_action(action, result, details=detail_str.strip(), user_override=user_override)
        return jsonify(success=True)
    except Exception as e:
        log_action('action_log', 'error', f"message={str(e)[:80]}")
        return jsonify(error=str(e)), 400

@app.route('/save_drawings', methods=['POST'])
def save_drawings():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = json.loads(request.data.decode('utf-8'))
        
        os.makedirs(os.path.dirname(DRAWINGS_FILE), exist_ok=True)
        deleted_count = sum(1 for f in data if f.get('properties', {}).get('deleted'))
        with open(DRAWINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        if APP_MODE == "server":
            try:
                log_action('save_drawings', 'ok', f"total={len(data)} deleted={deleted_count}")
            except Exception as e:
                pass

        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 400

@app.route('/merge_drawings')
def merge_drawings_route():
    try:
        if not os.path.exists(DRAWINGS_FILE):
            return jsonify(merged=[])

        with open(DRAWINGS_FILE, 'r') as f:
            drawings = json.load(f)
        with open(SHARED_FILE, 'r') as f:
            shared = json.load(f)

        def build_dict(features):
            d = {}
            for f in features:
                pid = f.get('properties', {}).get('_id')
                if pid is not None:
                    d[pid] = f
            return d

        drawings_dict = build_dict(drawings)
        shared_dict = build_dict(shared)
        merged_dict = {}

        all_ids = set(drawings_dict.keys()) | set(shared_dict.keys())
        for _id in all_ids:
            d_feat = drawings_dict.get(_id)
            s_feat = shared_dict.get(_id)
            if d_feat and s_feat:
                merged = d_feat.copy()
                merged_props = merged.get('properties', {}).copy()
                merged_props['deleted'] = d_feat['properties'].get('deleted', False) or s_feat['properties'].get('deleted', False)
                merged_props['hostile'] = d_feat['properties'].get('hostile', False) or s_feat['properties'].get('hostile', False)
                merged_props['color'] = s_feat['properties'].get('color', d_feat['properties'].get('color', 'blue'))
                merged['properties'] = merged_props
                merged_dict[_id] = merged
            elif d_feat:
                merged_dict[_id] = d_feat
            elif s_feat:
                merged_dict[_id] = s_feat

        merged_list = list(merged_dict.values())
        return jsonify(merged=merged_list)
    except Exception as e:
        return jsonify(error=str(e))

@app.route('/compute_path')
def compute_path():
    try:
        start_lat = float(request.args.get('start_lat'))
        start_lon = float(request.args.get('start_lon'))
        goal_lat = float(request.args.get('goal_lat'))
        goal_lon = float(request.args.get('goal_lon'))
        min_clearance_m = float(request.args.get('clearance', request.args.get('corridor', 0)))

        if not os.path.exists(DRAWINGS_FILE):
            return jsonify(error="Drawings file missing")
        with open(DRAWINGS_FILE, 'r') as f:
            drawings = json.load(f)

        hostile_features = [f for f in drawings if f['properties'].get('hostile') and not f['properties'].get('deleted')]
        print(f"Pathfinding: {len(drawings)} total drawings, {len(hostile_features)} marked as hostile")
        dstar.apply_hostile_zones(hostile_features, influence_radius_m=100)

        start_r, start_c = dstar.latlon_to_index(start_lat, start_lon)
        goal_r, goal_c = dstar.latlon_to_index(goal_lat, goal_lon)

        start_blocked = dstar.in_bounds(start_r, start_c) and dstar.hostile_mask[start_r, start_c]
        goal_blocked = dstar.in_bounds(goal_r, goal_c) and dstar.hostile_mask[goal_r, goal_c]

        if start_blocked or goal_blocked:
            return jsonify(
                error="Start or goal is inside a hostile zone. Move points outside hostile areas and retry."
            )

        start_clearance = dstar.hostile_distance_m[start_r, start_c] if dstar.in_bounds(start_r, start_c) else float('inf')
        goal_clearance = dstar.hostile_distance_m[goal_r, goal_c] if dstar.in_bounds(goal_r, goal_c) else float('inf')

        if start_clearance < min_clearance_m or goal_clearance < min_clearance_m:
            return jsonify(
                error="Start or goal does not meet the required hostile clearance. Move points or lower minimum clearance."
            )

        approx_dist_m = dstar.latlon_distance(start_lat, start_lon, goal_lat, goal_lon)
        retry_margins = [
            max(500.0, approx_dist_m * 0.4),
            max(1500.0, approx_dist_m * 0.9),
            None
        ]

        path = []
        for idx, margin_m in enumerate(retry_margins):
            attempt_path, attempt_debug = dstar.compute_path(
                (start_lat, start_lon),
                (goal_lat, goal_lon),
                min_clearance_m=min_clearance_m,
                search_margin_m=margin_m
            )

            if attempt_path:
                path = attempt_path
                break

        if not path:
            return jsonify(
                error="No path found with the current hostile-clearance requirement. Lower the clearance or move points."
            )

        total_dist = 0
        R = 6371000
        for i in range(1, len(path)):
            lat1, lon1 = path[i-1]
            lat2, lon2 = path[i]
            dLat = math.radians(lat2 - lat1)
            dLon = math.radians(lon2 - lon1)
            a = math.sin(dLat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            total_dist += R * c

        est_time_min = round(total_dist / 1.4 / 60, 1)
        
        risk_level, min_distance = dstar.calculate_path_risk(path)
        
        return jsonify(
            path=path, 
            distance_m=round(total_dist), 
            estimated_time_min=est_time_min,
            risk_level=risk_level,
            min_hostile_distance_m=round(min_distance) if min_distance != float('inf') else None
        )

    except Exception as e:
        return jsonify(error=str(e))

@app.route('/tile_bounds')
def tile_bounds():
    zoom = 11
    zoom_dir = os.path.join(TILE_DIR, str(zoom))
    if not os.path.exists(zoom_dir):
        return jsonify(error=f"Zoom {zoom} folder missing"), 404

    x_tiles = [int(d) for d in os.listdir(zoom_dir) if d.isdigit()]
    min_x, max_x = min(x_tiles), max(x_tiles)
    y_tiles_all = []

    for x in x_tiles:
        y_dir = os.path.join(zoom_dir, str(x))
        if os.path.exists(y_dir):
            y_tiles = [int(f.split('.')[0]) for f in os.listdir(y_dir) if f.endswith('.png')]
            y_tiles_all.extend(y_tiles)

    min_y, max_y = min(y_tiles_all), max(y_tiles_all)

    def tile2lon(x, z):
        return x / (2 ** z) * 360 - 180

    def tile2lat(y, z):
        n = math.pi - 2 * math.pi * y / (2 ** z)
        return math.degrees(math.atan(np.sinh(n)))

    west = tile2lon(min_x, zoom)
    east = tile2lon(max_x + 1, zoom)
    north = tile2lat(min_y, zoom)
    south = tile2lat(max_y + 1, zoom)

    center_x = (min_x + max_x) / 2 + 0.5
    center_y = (min_y + max_y) / 2 + 0.5
    center_lon = tile2lon(center_x, zoom)
    center_lat = tile2lat(center_y, zoom)

    return jsonify(bounds=[[south, west], [north, east]], center=[center_lat, center_lon], minZoom=2, maxZoom=18)

if APP_MODE == "server":
    @app.route('/monitor')
    def monitor():
        return render_template('monitor.html')

    @app.route('/monitor/data')
    def monitor_data():
        try:
            traffic_log = os.path.join(LOGS_DIR, 'traffic.log')
            actions_log = os.path.join(LOGS_DIR, 'actions.log')
            
            traffic_entries = []
            actions_entries = []
            total_traffic = 0
            total_actions = 0
            active_ips = set()
            active_clients = {}  # ip -> {last_seen, user, path}
            
            now = datetime.now()
            five_min_ago = now - timedelta(minutes=5)
            
            if os.path.exists(traffic_log):
                with open(traffic_log, 'r') as f:
                    lines = f.readlines()
                    total_traffic = len(lines)
                    recent_lines = lines[-100:]
                    traffic_entries = [line.strip() for line in recent_lines if line.strip()]
                    
                    for line in lines:
                        try:
                            timestamp_str = line.split('|')[0].strip()
                            entry_time = datetime.strptime(timestamp_str.rsplit(',', 1)[0], '%Y-%m-%d %H:%M:%S')
                            
                            if entry_time >= five_min_ago:
                                ip_match = re.search(r'ip=([\d\.]+)', line)
                                if ip_match:
                                    ip = ip_match.group(1)
                                    active_ips.add(ip)
                                    
                                    if ip not in active_clients or entry_time > active_clients[ip]['last_seen']:
                                        path_match = re.search(r'path=([^\s]+)', line)
                                        method_match = re.search(r'method=(\w+)', line)
                                        
                                        active_clients[ip] = {
                                            'last_seen': entry_time,
                                            'last_path': path_match.group(1) if path_match else '-',
                                            'last_method': method_match.group(1) if method_match else '-'
                                        }
                        except Exception:
                            pass
            
            if os.path.exists(actions_log):
                with open(actions_log, 'r') as f:
                    lines = f.readlines()
                    total_actions = len(lines)
                    recent_lines = lines[-50:]
                    actions_entries = [line.strip() for line in recent_lines if line.strip()]
            
            active_clients_list = [
                {
                    'ip': ip,
                    'last_seen': info['last_seen'].strftime('%Y-%m-%d %H:%M:%S'),
                    'last_path': info['last_path'],
                    'last_method': info['last_method']
                }
                for ip, info in active_clients.items()
            ]
            active_clients_list.sort(key=lambda x: x['last_seen'], reverse=True)
            
            return jsonify({
                'traffic': traffic_entries[::-1],
                'actions': actions_entries[::-1],
                'total_traffic': total_traffic,
                'total_actions': total_actions,
                'active_sessions': len(active_ips),
                'active_clients': active_clients_list
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/monitor/clear', methods=['POST'])
    def monitor_clear():
        """Truncate traffic/actions logs so clearing the dashboard is persistent."""
        try:
            log_type = request.args.get('type', 'all')
            traffic_log = os.path.join(LOGS_DIR, 'traffic.log')
            actions_log = os.path.join(LOGS_DIR, 'actions.log')

            cleared = []
            if log_type in ('all', 'traffic'):
                open(traffic_log, 'w').close()
                cleared.append('traffic')
            if log_type in ('all', 'actions'):
                open(actions_log, 'w').close()
                cleared.append('actions')

            return jsonify(success=True, cleared=cleared)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)

    if not os.path.exists(DRAWINGS_FILE):
        with open(DRAWINGS_FILE, 'w') as f:
            json.dump(DEMO_DRAWINGS, f, indent=2)
        print("[Init] Created demo drawings.json")

    if not os.path.exists(SHARED_FILE):
        with open(SHARED_FILE, 'w') as f:
            json.dump(DEMO_SHARED, f, indent=2)
        print("[Init] Created demo shared.json")

    env_port = (os.getenv("PORT") or "").strip()
    port = args.port if args.port is not None else (int(env_port) if env_port.isdigit() else None)
    if port is not None and not (1 <= port <= 65535):
        print(f"[Startup] Invalid port: {port}. Use a value between 1 and 65535.")
        sys.exit(1)

    if APP_MODE == "server":
        if not os.environ.get("WERKZEUG_RUN_MAIN"):
            merge_thread.start()
        if port is None:
            port = 5001
        print(f"Starting POPMAP SERVER on port {port}")

        ngrok_url = None
        if args.ngrok:
            ngrok_url = start_ngrok_tunnel(port)
            if ngrok_url:
                print(f"[Server] Using ngrok public URL: {ngrok_url}")
                os.environ["PUBLIC_SERVER_URL"] = ngrok_url
            else:
                print("[Server] ngrok unavailable; falling back to detected local/network URL.")

        public_server_url = detect_public_url(port, use_ngrok=args.ngrok)

        try:
            connection_id = generate_connection_id(public_server_url, CONNECTION_ID_SECRET or None)
            print(f"[Server] Connection URL: {public_server_url}")
            print(f"[Server] Connection ID: {connection_id}")
            print("[Server] Share this ID with clients. It expires in 7 days by default.")
        except Exception as e:
            print(f"[Server] Failed to generate connection ID: {e}")
    else:
        if port is None:
            port = 5000
        print(f"Starting POPMAP CLIENT on port {port}")

    app.run(debug=False, use_reloader=False, port=port, host='0.0.0.0')
