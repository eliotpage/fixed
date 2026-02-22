import os
import json
import math
import threading
import time
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_mail import Mail, Message
from hashing import generate_otp, verify_otp
from dstar import DStarLite
from dotenv import load_dotenv
import numpy as np

# ===================== DEMO DATA =====================
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

DRAWINGS_FILE = os.path.join('static', 'drawings.json')
SHARED_FILE = os.path.join('static', 'shared.json')
TILE_DIR = os.path.join('static', 'tiles')
DEM_PATH = os.path.join('static', 'output_be.tif')
MERGE_INTERVAL = 10  # seconds

# ===================== APP SETUP =====================
app = Flask(__name__)
load_dotenv()  # Load secrets
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

# ===================== D* LITE =====================
dstar = DStarLite(DEM_PATH, tile_dir=TILE_DIR, zoom=11)

# ===================== MERGE FUNCTION =====================
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

                # Both exist → merge hostile/color/deleted
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
merge_thread.start()

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
        print("[Mail Error]", e)
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

# ===================== SAVE/LOAD =====================
@app.route('/save_drawings', methods=['POST'])
def save_drawings():
    # Handle both regular JSON and sendBeacon blob
    try:
        if request.is_json:
            data = request.get_json()
        else:
            # sendBeacon sends as blob
            data = json.loads(request.data.decode('utf-8'))
        
        os.makedirs(os.path.dirname(DRAWINGS_FILE), exist_ok=True)
        with open(DRAWINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[Save] Saved {len(data)} drawings")
        return jsonify(success=True)
    except Exception as e:
        print(f"[Save Error] {e}")
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

        # Merge hostile/color/deleted as above
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

# ===================== PATHFINDING =====================
@app.route('/compute_path')
def compute_path():
    try:
        start_lat = float(request.args.get('start_lat'))
        start_lon = float(request.args.get('start_lon'))
        goal_lat = float(request.args.get('goal_lat'))
        goal_lon = float(request.args.get('goal_lon'))
        corridor_m = float(request.args.get('corridor', 50))

        # Load current drawings
        if not os.path.exists(DRAWINGS_FILE):
            return jsonify(error="Drawings file missing")
        with open(DRAWINGS_FILE, 'r') as f:
            drawings = json.load(f)

        # Filter hostile features (deleted ones ignored)
        hostile_features = [f for f in drawings if f['properties'].get('hostile') and not f['properties'].get('deleted')]
        print(f"[Path] Computing path with {len(hostile_features)} hostile features out of {len(drawings)} total drawings")
        for hf in hostile_features:
            print(f"  - Hostile {hf['geometry']['type']}: ID={hf['properties']['_id']}, Color={hf['properties'].get('color')}")

        # Apply hostile zones to cost map: entire hostile shape blocked, influence slope around
        dstar.apply_hostile_zones(hostile_features, influence_radius_m=100)

        # Compute path using D* Lite (with corridor)
        path, debug_msgs = dstar.compute_path(
            (start_lat, start_lon),
            (goal_lat, goal_lon),
            corridor_m=corridor_m,
            debug=True
        )
        if not path:
            return jsonify(error="No path found", debug=debug_msgs)

        # Compute distance & estimated time
        total_dist = 0
        R = 6371000  # radius of the Earth in meters
        for i in range(1, len(path)):
            lat1, lon1 = path[i-1]
            lat2, lon2 = path[i]
            dLat = math.radians(lat2 - lat1)
            dLon = math.radians(lon2 - lon1)
            a = math.sin(dLat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            total_dist += R * c

        est_time_min = round(total_dist / 1.4 / 60, 1)
        
        # Calculate path risk based on proximity to hostile zones
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

# ===================== INIT =====================
if __name__ == "__main__":
    os.makedirs('static', exist_ok=True)

    if not os.path.exists(DRAWINGS_FILE):
        with open(DRAWINGS_FILE, 'w') as f:
            json.dump(DEMO_DRAWINGS, f, indent=2)
        print("[Init] Created demo drawings.json")

    if not os.path.exists(SHARED_FILE):
        with open(SHARED_FILE, 'w') as f:
            json.dump(DEMO_SHARED, f, indent=2)
        print("[Init] Created demo shared.json")

    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        merge_thread = threading.Thread(target=merge_drawings_loop, daemon=True)
        merge_thread.start()

    app.run(debug=True)