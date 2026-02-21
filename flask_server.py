import os
import json
import math
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_mail import Mail, Message
from hashing import generate_otp, verify_otp
from dstar import DStarLite
from dotenv import load_dotenv
import numpy as np
import threading
import time

# ===================== DEMO DATA =====================
DEMO_DRAWINGS = [
    {
        "type": "Feature",
        "properties": {"_id": 1, "deleted": False, "color": "blue", "isMarker": True},
        "geometry": {"type": "Point", "coordinates": [33.100, 35.100]}
    },
    {
        "type": "Feature",
        "properties": {"_id": 2, "deleted": True, "color": "red"},
        "geometry": {"type": "LineString", "coordinates": [[33.101, 35.101], [33.102, 35.102]]}
    },
    {
        "type": "Feature",
        "properties": {"_id": 3, "deleted": False, "color": "green"},
        "geometry": {"type": "Polygon", "coordinates": [[[33.103, 35.103], [33.104, 35.104], [33.105, 35.103], [33.103, 35.103]]]}
    }
]

DEMO_SHARED = [
    {
        "type": "Feature",
        "properties": {"_id": 2, "deleted": True, "color": "red"},
        "geometry": {"type": "LineString", "coordinates": [[33.101, 35.101], [33.102, 35.102]]}
    },
    {
        "type": "Feature",
        "properties": {"_id": 3, "deleted": True, "color": "green"},
        "geometry": {"type": "Polygon", "coordinates": [[[33.103, 35.103], [33.104, 35.104], [33.105, 35.103], [33.103, 35.103]]]}
    },
    {
        "type": "Feature",
        "properties": {"_id": 4, "deleted": False, "color": "orange", "isMarker": True},
        "geometry": {"type": "Point", "coordinates": [33.106, 35.106]}
    }
]

MERGE_DIR = '/workspaces/fixed'  # directory to watch for shared.json
MERGE_INTERVAL = 10    # seconds between checks

def merge_drawings():
    while True:
        shared_path = os.path.join(MERGE_DIR, 'shared.json')
        if os.path.exists(shared_path):
            try:
                with open(DRAWINGS_FILE, 'r') as f:
                    drawings = json.load(f)
                with open(shared_path, 'r') as f:
                    shared = json.load(f)

                # Build dicts keyed by _id
                def build_dict(features):
                    return {f['properties']['_id']: f for f in features}
                
                drawings_dict = build_dict(drawings)
                shared_dict = build_dict(shared)
                merged_dict = {}
                all_ids = set(drawings_dict.keys()) | set(shared_dict.keys())

                for _id in all_ids:
                    d_feat = drawings_dict.get(_id)
                    s_feat = shared_dict.get(_id)
                    
                    # Both deleted → skip
                    if d_feat and s_feat and d_feat['properties'].get('deleted') and s_feat['properties'].get('deleted'):
                        continue
                    # Only in one file → keep
                    if d_feat and not s_feat:
                        merged_dict[_id] = d_feat
                        continue
                    if s_feat and not d_feat:
                        merged_dict[_id] = s_feat
                        continue
                    # In both → handle deletion
                    merged = d_feat.copy()
                    merged_props = merged['properties'].copy()
                    if d_feat['properties'].get('deleted') or s_feat['properties'].get('deleted'):
                        merged_props['deleted'] = True
                    merged['properties'] = merged_props
                    merged_dict[_id] = merged

                merged_list = list(merged_dict.values())
                
                # Overwrite drawings.json with merged
                with open(DRAWINGS_FILE, 'w') as f:
                    json.dump(merged_list, f, indent=2)

                print(f"[Merge] Merged {len(drawings)} + {len(shared)} → {len(merged_list)} features")

            except Exception as e:
                print(f"[Merge] Error merging drawings: {e}")

        time.sleep(MERGE_INTERVAL)

merge_thread = threading.Thread(target=merge_drawings, daemon=True)
merge_thread.start()

# ===================== APP SETUP =====================
app = Flask(__name__)
load_dotenv()

# Load secrets
app.secret_key = os.getenv("SECRET_KEY")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

if not app.secret_key or not MAIL_USERNAME or not MAIL_PASSWORD:
    raise RuntimeError("Missing required environment variables: SECRET_KEY, MAIL_USERNAME, MAIL_PASSWORD")

# ===================== MAIL CONFIG =====================
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD
)
mail = Mail(app)

# ===================== FILES & D* =====================
DRAWINGS_FILE = os.path.join('static', 'drawings.json')
TILE_DIR = os.path.join('static', 'tiles')
DEM_PATH = os.path.join('static', 'output_be.tif')

# Initialize D* Lite with DEM
dstar = DStarLite(DEM_PATH)

# ===================== ROUTES =====================
@app.route('/')
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/map')
def map_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# ===================== OTP =====================
@app.route('/request_otp', methods=['POST'])
def request_otp():
    data = request.get_json()
    user = data.get('user')
    if not user:
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
        return jsonify(success=True)
    except Exception as e:
        print("Error sending OTP:", e)
        return jsonify(success=False, error="Failed to send OTP")

@app.route('/login_verify', methods=['POST'])
def login_verify():
    data = request.get_json()
    user = data.get('user')
    token = data.get('otp')
    if not user or not token:
        return jsonify(success=False, error="Missing data")
    if verify_otp(app.secret_key, user, token):
        session['user'] = user
        return jsonify(success=True)
    return jsonify(success=False, error="Invalid or expired OTP")

# ===================== DRAWINGS =====================
@app.route('/save_drawings', methods=['POST'])
def save_drawings():
    data = request.get_json()
    os.makedirs(os.path.dirname(DRAWINGS_FILE), exist_ok=True)
    with open(DRAWINGS_FILE, 'w') as f:
        json.dump(data, f)
    return jsonify(success=True)

# ===================== PATHFINDING =====================
@app.route('/compute_path')
def compute_path():
    try:
        # NOTE: front-end sends lon,lat order
        start_lon = float(request.args.get('start_lon'))
        start_lat = float(request.args.get('start_lat'))
        goal_lon  = float(request.args.get('goal_lon'))
        goal_lat  = float(request.args.get('goal_lat'))
        corridor_m = float(request.args.get('corridor', 50))

        path, debug_msgs = dstar.compute_path(
            (start_lat, start_lon),
            (goal_lat, goal_lon),
            corridor_m=corridor_m,
            debug=True
        )

        if not path:
            return jsonify({"error": "No path found", "debug": debug_msgs})

        # Compute total distance
        total_dist = 0
        R = 6371000
        for i in range(1, len(path)):
            lat1, lon1 = path[i-1]
            lat2, lon2 = path[i]
            dLat = math.radians(lat2 - lat1)
            dLon = math.radians(lon2 - lon1)
            a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            total_dist += R * c

        est_time_min = round(total_dist / 1.4 / 60, 1)

        return jsonify({"path": path, "debug": debug_msgs, "distance_m": round(total_dist), "estimated_time_min": est_time_min})

    except Exception as e:
        return jsonify({"error": str(e), "debug": [str(e)]})

# ===================== TILE BOUNDS =====================
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

    def tile2lon(x, z): return x / (2**z) * 360 - 180
    def tile2lat(y, z):
        n = math.pi - 2 * math.pi * y / (2**z)
        return math.degrees(math.atan(np.sinh(n)))

    west = tile2lon(min_x, zoom)
    east = tile2lon(max_x + 1, zoom)
    north = tile2lat(min_y, zoom)
    south = tile2lat(max_y + 1, zoom)

    center_x = (min_x + max_x)/2 + 0.5
    center_y = (min_y + max_y)/2 + 0.5
    center_lon = tile2lon(center_x, zoom)
    center_lat = tile2lat(center_y, zoom)

    return jsonify({
        'bounds': [[south, west], [north, east]],
        'center': [center_lat, center_lon],
        'minZoom': 11,
        'maxZoom': 16
    })

if __name__ == "__main__":
    os.makedirs('static', exist_ok=True)

    # Initialize drawings.json if missing
    if not os.path.exists(DRAWINGS_FILE):
        with open(DRAWINGS_FILE, 'w') as f:
            json.dump(DEMO_DRAWINGS, f, indent=2)
        print("[Init] Created demo drawings.json")

    # Initialize shared.json if missing
    shared_file = os.path.join('static', 'shared.json')
    if not os.path.exists(shared_file):
        with open(shared_file, 'w') as f:
            json.dump(DEMO_SHARED, f, indent=2)
        print("[Init] Created demo shared.json")

    # Start merge thread (will run periodically after first interval)
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        merge_thread = threading.Thread(target=merge_drawings, daemon=True)
        merge_thread.start()

    app.run(debug=True)