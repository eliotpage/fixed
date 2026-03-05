"""
Unified POPMAP Application
Runs in either CLIENT or SERVER mode based on APP_MODE environment variable or --server flag.

CLIENT mode (default, port 5000):
  - Map interface for drawing routes and obstacles
  - Communicates with server for authentication and pathfinding
  - Displays merged drawings and computed paths

SERVER mode (port 5001):
  - Authentication via OTP email
  - Pathfinding computation
  - Traffic monitoring dashboard
  - Background thread for merging drawings every 10 seconds
"""

import os
import json
import math
import threading
import time
import re
import sys
import argparse
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from lib.dstar import DStarLite
from dotenv import load_dotenv
import numpy as np
import requests

# Parse command line arguments
parser = argparse.ArgumentParser(description='POPMAP Application')
parser.add_argument('--server', action='store_true', help='Run in server mode (default: client mode)')
args = parser.parse_args()

# Determine app mode from environment variable or CLI flag
APP_MODE = os.getenv("APP_MODE", "server" if args.server else "client").lower()
if APP_MODE not in ["client", "server"]:
    APP_MODE = "client"

# Demo data for testing
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

DRAWINGS_FILE = os.path.join('data', 'drawings.json')
SHARED_FILE = os.path.join('data', 'shared.json')
TILE_DIR = os.path.join('static', 'tiles')
DEM_PATH = os.path.join('static', 'output_be.tif')
MERGE_INTERVAL = 10

app = Flask(__name__)
load_dotenv()

# Ensure logs directory exists for action logging in all modes
os.makedirs('logs', exist_ok=True)


# Action logging helper (available in both modes)
def log_action(action, result, details="", user_override=None):
    # Prefer forwarded IP when behind proxy
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
        with open('logs/actions.log', 'a') as f:
            f.write(log_entry + '\n')
    except Exception as e:
        print(f"Error logging action: {e}")

# Server mode specific initialization
if APP_MODE == "server":
    try:
        from flask_mail import Mail, Message
        from lib.hashing import generate_otp, verify_otp
        
        app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        MAIL_USERNAME = os.getenv("MAIL_USERNAME")
        MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
        
        # Email is optional - server works in demo mode without it
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
            print("[Server] ⚠️  Email not configured. Authentication endpoints will not send emails.")
            print("        Set MAIL_USERNAME and MAIL_PASSWORD environment variables to enable email.")
        
    except ImportError:
        print("Warning: flask_mail not installed. Email functionality will not work in server mode.")
        mail = None
else:
    # Client mode
    app.secret_key = os.getenv("SECRET_KEY", "client-secret-key-change-in-production")
    mail = None

SERVER_URL = os.getenv("SERVER_URL", "http://localhost")

# Initialize pathfinding engine with terrain data
dstar = DStarLite(DEM_PATH, tile_dir=TILE_DIR, zoom=11)

# ============================================================
# SERVER MODE: Traffic logging and background processes
# ============================================================

if APP_MODE == "server":
    os.makedirs('logs', exist_ok=True)
    
    # Traffic logging middleware
    @app.before_request
    def log_request():
        # Skip monitoring its own dashboard traffic
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

            log_entry = (
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} | "
                f"ip={request.remote_addr} "
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
                with open('logs/traffic.log', 'a') as f:
                    f.write(log_entry + '\n')
            except Exception as e:
                print(f"Error logging traffic: {e}")
        return response

    # Action logging handled globally; see action_log route outside server guard

    # Background thread to merge drawings with shared data every 10 seconds
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
                print("[Merge Error]", e)

            time.sleep(MERGE_INTERVAL)

    merge_thread = threading.Thread(target=merge_drawings_loop, daemon=True)

# ============================================================
# COMMON ROUTES (available in both modes)
# ============================================================

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

# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

# OTP request - relay to server (CLIENT mode) or send directly (SERVER mode)
@app.route('/request_otp', methods=['POST'])
def request_otp():
    data = request.get_json()
    user = data.get('user')
    if not user:
        return jsonify(success=False, error="Missing email")
    
    if APP_MODE == "client":
        try:
            # Call server to send OTP email
            response = requests.post(f"{SERVER_URL}/send_otp", json={"user": user}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return jsonify(success=result.get('success', False), error=result.get('error', ''))
            else:
                return jsonify(success=False, error="Server error")
        except Exception as e:
            print(f"[Request OTP Error] {e}")
            return jsonify(success=False, error="Could not reach authentication server")
    else:
        # Server mode - send OTP directly
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
            print("[Mail Error]", e)
            return jsonify(success=False, error="Failed to send OTP")

# OTP verification - relay to server (CLIENT mode) or verify directly (SERVER mode)
@app.route('/login_verify', methods=['POST'])
def login_verify():
    data = request.get_json()
    user = data.get('user')
    token = data.get('otp')
    if not user or not token:
        return jsonify(success=False, error="Missing data")
    
    if APP_MODE == "client":
        try:
            # Call server to verify OTP
            response = requests.post(f"{SERVER_URL}/verify_otp", json={"user": user, "otp": token}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    session['user'] = user
                    return jsonify(success=True)
                else:
                    return jsonify(success=False, error=result.get('error', 'Invalid OTP'))
            else:
                return jsonify(success=False, error="Server error")
        except Exception as e:
            print(f"[Login Verify Error] {e}")
            return jsonify(success=False, error="Could not reach authentication server")
    else:
        # Server mode - verify OTP directly
        if verify_otp(app.secret_key, user, token):
            session['user'] = user
            return jsonify(success=True)
        return jsonify(success=False, error="Invalid or expired OTP")

# API endpoint for client apps to send OTP (SERVER mode only)
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
        print("[Mail Error]", e)
        log_action('send_otp', 'error', f'user={user} error={str(e)[:50]}')
        return jsonify(success=False, error="Failed to send OTP")

# API endpoint for client apps to verify OTP (SERVER mode only)
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

# ============================================================
# DRAWING & MAP ROUTES
# ============================================================

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

    # If running in client mode with a SERVER_URL, forward to server for central logging
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
                # Fall back to local log if server rejects
                log_action('action_log_forward', 'error', f"status={resp.status_code}")
        except Exception as e:
            log_action('action_log_forward', 'error', f"message={str(e)[:80]}")

    # Local logging (server mode or client fallback)
    try:
        log_action(action, result, details=detail_str.strip(), user_override=user_override)
        return jsonify(success=True)
    except Exception as e:
        log_action('action_log', 'error', f"message={str(e)[:80]}")
        return jsonify(error=str(e)), 400

# Save user's drawings to local JSON database
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
        print(f"[Save] Saved {len(data)} drawings")

        if APP_MODE == "server":
            try:
                log_action('save_drawings', 'ok', f"total={len(data)} deleted={deleted_count}")
            except Exception as e:
                print(f"[Action Log Error] {e}")

        return jsonify(success=True)
    except Exception as e:
        print(f"[Save Error] {e}")
        return jsonify(success=False, error=str(e)), 400

# Merge user and shared drawings
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

# Calculate optimal path avoiding hostile zones
@app.route('/compute_path')
def compute_path():
    try:
        start_lat = float(request.args.get('start_lat'))
        start_lon = float(request.args.get('start_lon'))
        goal_lat = float(request.args.get('goal_lat'))
        goal_lon = float(request.args.get('goal_lon'))
        corridor_m = float(request.args.get('corridor', 50))

        if not os.path.exists(DRAWINGS_FILE):
            return jsonify(error="Drawings file missing")
        with open(DRAWINGS_FILE, 'r') as f:
            drawings = json.load(f)

        hostile_features = [f for f in drawings if f['properties'].get('hostile') and not f['properties'].get('deleted')]
        print(f"[Path] Computing path with {len(hostile_features)} hostile features out of {len(drawings)} total drawings")
        for hf in hostile_features:
            print(f"  - Hostile {hf['geometry']['type']}: ID={hf['properties']['_id']}, Color={hf['properties'].get('color')}")

        dstar.apply_hostile_zones(hostile_features, influence_radius_m=100)

        debug_msgs = []
        start_r, start_c = dstar.latlon_to_index(start_lat, start_lon)
        goal_r, goal_c = dstar.latlon_to_index(goal_lat, goal_lon)

        start_blocked = dstar.in_bounds(start_r, start_c) and dstar.hostile_mask[start_r, start_c]
        goal_blocked = dstar.in_bounds(goal_r, goal_c) and dstar.hostile_mask[goal_r, goal_c]

        if start_blocked or goal_blocked:
            if start_blocked:
                debug_msgs.append("Start point lies inside a hostile zone")
            if goal_blocked:
                debug_msgs.append("Goal point lies inside a hostile zone")
            return jsonify(
                error="Start or goal is inside a hostile zone. Move points outside hostile areas and retry.",
                debug=debug_msgs
            )

        retry_corridors = [corridor_m]
        for candidate in (max(corridor_m * 2, 100), max(corridor_m * 4, 250), None):
            if candidate not in retry_corridors:
                retry_corridors.append(candidate)

        path = []
        for idx, attempt_corridor in enumerate(retry_corridors):
            if idx > 0:
                debug_msgs.append(f"Retrying with wider corridor: {attempt_corridor if attempt_corridor is not None else 'full-map search'}")

            attempt_path, attempt_debug = dstar.compute_path(
                (start_lat, start_lon),
                (goal_lat, goal_lon),
                corridor_m=attempt_corridor,
                debug=True
            )
            debug_msgs.extend(attempt_debug)

            if attempt_path:
                path = attempt_path
                break

        if not path:
            return jsonify(
                error="No path found. Try increasing corridor width or moving points around hostile barriers.",
                debug=debug_msgs
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
            debug=debug_msgs, 
            distance_m=round(total_dist), 
            estimated_time_min=est_time_min,
            risk_level=risk_level,
            min_hostile_distance_m=round(min_distance) if min_distance != float('inf') else None
        )

    except Exception as e:
        return jsonify(error=str(e), debug=[str(e)])

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

    return jsonify(bounds=[[south, west], [north, east]], center=[center_lat, center_lon], minZoom=11, maxZoom=16)

# ============================================================
# SERVER MODE: MONITORING ROUTES
# ============================================================

if APP_MODE == "server":
    @app.route('/monitor')
    def monitor():
        return render_template('monitor.html')

    @app.route('/monitor/data')
    def monitor_data():
        try:
            traffic_log = os.path.join('logs', 'traffic.log')
            actions_log = os.path.join('logs', 'actions.log')
            
            traffic_entries = []
            actions_entries = []
            total_traffic = 0
            total_actions = 0
            active_ips = set()
            
            # Get current time and 5 minutes ago
            now = datetime.now()
            five_min_ago = now - timedelta(minutes=5)
            
            if os.path.exists(traffic_log):
                with open(traffic_log, 'r') as f:
                    lines = f.readlines()
                    total_traffic = len(lines)
                    recent_lines = lines[-100:]
                    traffic_entries = [line.strip() for line in reversed(recent_lines) if line.strip()]
                    
                    # Count active sessions from last 5 minutes
                    for line in lines:
                        try:
                            # Extract timestamp: format is "YYYY-MM-DD HH:MM:SS,mmm"
                            timestamp_str = line.split('|')[0].strip()
                            entry_time = datetime.strptime(timestamp_str.rsplit(',', 1)[0], '%Y-%m-%d %H:%M:%S')
                            
                            if entry_time >= five_min_ago:
                                ip_match = re.search(r'ip=([\d\.]+)', line)
                                if ip_match:
                                    active_ips.add(ip_match.group(1))
                        except Exception:
                            pass
            
            if os.path.exists(actions_log):
                with open(actions_log, 'r') as f:
                    lines = f.readlines()
                    total_actions = len(lines)
                    recent_lines = lines[-50:]
                    actions_entries = [line.strip() for line in reversed(recent_lines) if line.strip()]
            
            return jsonify({
                'traffic': traffic_entries,
                'actions': actions_entries,
                'total_traffic': total_traffic,
                'total_actions': total_actions,
                'active_sessions': len(active_ips)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/monitor/clear', methods=['POST'])
    def monitor_clear():
        """Truncate traffic/actions logs so clearing the dashboard is persistent."""
        try:
            log_type = request.args.get('type', 'all')
            traffic_log = os.path.join('logs', 'traffic.log')
            actions_log = os.path.join('logs', 'actions.log')

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

# ============================================================
# APPLICATION STARTUP
# ============================================================

if __name__ == "__main__":
    os.makedirs('static', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    if not os.path.exists(DRAWINGS_FILE):
        with open(DRAWINGS_FILE, 'w') as f:
            json.dump(DEMO_DRAWINGS, f, indent=2)
        print("[Init] Created demo drawings.json")

    if not os.path.exists(SHARED_FILE):
        with open(SHARED_FILE, 'w') as f:
            json.dump(DEMO_SHARED, f, indent=2)
        print("[Init] Created demo shared.json")

    if APP_MODE == "server":
        if not os.environ.get("WERKZEUG_RUN_MAIN"):
            merge_thread.start()
        port = 5001
        print(f"Starting POPMAP SERVER on port {port}")
    else:
        port = 5000
        print(f"Starting POPMAP CLIENT on port {port}")

    app.run(debug=False, port=port, host='0.0.0.0')
