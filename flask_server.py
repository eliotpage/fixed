from flask import Flask, render_template, request, jsonify
import os, json, math, time
from hashing import generate_otp, verify_otp  # import your OTP functions

app = Flask(__name__)

DRAWINGS_FILE = os.path.join('static', 'drawings.json')
TILE_DIR = os.path.join('static', 'tiles')

SECRET_KEY = "supersecret"  # use a real secret in production

# ------------------- Pages -------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

# ------------------- OTP / Login API -------------------
@app.route('/request_otp', methods=['POST'])
def request_otp():
    data = request.get_json()
    user = data.get('user')
    if not user:
        return jsonify(success=False, error="User required")
    
    # generate OTP
    token = generate_otp(SECRET_KEY, user)
    # In production, you would send OTP via email/SMS instead of returning it
    return jsonify(success=True, otp=token)

@app.route('/login_verify', methods=['POST'])
def login_verify():
    data = request.get_json()
    user = data.get('user')
    otp = data.get('otp')
    if not user or not otp:
        return jsonify(success=False, error="User and OTP required")
    
    if verify_otp(SECRET_KEY, user, otp):
        return jsonify(success=True)
    else:
        return jsonify(success=False, error="Invalid or expired OTP")

# ------------------- Existing routes -------------------
@app.route('/save_drawings', methods=['POST'])
def save_drawings():
    data = request.get_json()
    os.makedirs(os.path.dirname(DRAWINGS_FILE), exist_ok=True)
    with open(DRAWINGS_FILE, 'w') as f:
        json.dump(data, f)
    return jsonify(success=True)

@app.route('/compute_path')
def compute_path():
    try:
        start_lat = float(request.args.get('start_lat'))
        start_lon = float(request.args.get('start_lon'))
        goal_lat = float(request.args.get('goal_lat'))
        goal_lon = float(request.args.get('goal_lon'))
        path = [[start_lat, start_lon], [goal_lat, goal_lon]]
        return jsonify(path)
    except Exception as e:
        return jsonify(error=str(e))

@app.route('/tile_bounds')
def tile_bounds():
    zoom = 11
    zoom_dir = os.path.join(TILE_DIR, str(zoom))
    if not os.path.exists(zoom_dir):
        return jsonify(error=f"Zoom {zoom} folder missing"), 404

    # List X tiles
    x_tiles = [int(d) for d in os.listdir(zoom_dir) if d.isdigit()]
    if not x_tiles: return jsonify(error="No X tiles for zoom 11"), 404
    min_x, max_x = min(x_tiles), max(x_tiles)

    # List Y tiles for each X
    y_tiles_all = []
    for x in x_tiles:
        y_dir = os.path.join(zoom_dir, str(x))
        if os.path.exists(y_dir):
            y_tiles = [int(f.split('.')[0]) for f in os.listdir(y_dir) if f.endswith('.png')]
            y_tiles_all.extend(y_tiles)
    if not y_tiles_all: return jsonify(error="No Y tiles for zoom 11"), 404
    min_y, max_y = min(y_tiles_all), max(y_tiles_all)

    # Convert tile numbers to lat/lon
    def tile2lon(x, z): return x / (2**z) * 360 - 180
    def tile2lat(y, z):
        n = math.pi - 2 * math.pi * y / (2**z)
        return math.degrees(math.atan(math.sinh(n)))

    # Bounds match exactly the tiles
    west = tile2lon(min_x, zoom)
    east = tile2lon(max_x + 1, zoom)
    north = tile2lat(min_y, zoom)
    south = tile2lat(max_y + 1, zoom)

    # Center = exact center of tiles
    center_x = (min_x + max_x) / 2 + 0.5
    center_y = (min_y + max_y) / 2 + 0.5
    center_lon = tile2lon(center_x, zoom)
    center_lat = tile2lat(center_y, zoom)

    return jsonify({
        'bounds': [[south, west], [north, east]],
        'center': [center_lat, center_lon],
        'minZoom': 9,
        'maxZoom': 14
    })



if __name__ == "__main__":
    app.run(debug=True)
