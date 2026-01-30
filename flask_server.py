from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os, json, math, time
from hashing import generate_otp, verify_otp
from dstar import DStar

app = Flask(__name__)
app.secret_key = "supersecret_flask_key"  # required for sessions

DRAWINGS_FILE = os.path.join('static', 'drawings.json')
TILE_DIR = os.path.join('static', 'tiles')
SECRET = "supersecretkey"

# Initialize DStar
dstar = DStar()

# Load obstacles from drawings.json
def load_obstacles():
    try:
        with open(DRAWINGS_FILE) as f:
            dstar.obstacles = json.load(f)
    except FileNotFoundError:
        dstar.obstacles = []

# ================= LOGIN & SESSION =================
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/map')
def map_page():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# ================= OTP =================
@app.route('/request_otp', methods=['POST'])
def request_otp():
    data = request.get_json()
    user = data.get('user')
    if not user:
        return jsonify(success=False, error="Missing user")
    token = generate_otp(SECRET, user)
    return jsonify(success=True, otp=token)  # dev only

@app.route('/login_verify', methods=['POST'])
def login_verify():
    data = request.get_json()
    user = data.get('user')
    token = data.get('otp')
    if not user or not token:
        return jsonify(success=False, error="Missing user or OTP")
    if verify_otp(SECRET, user, token):
        session['user'] = user
        return jsonify(success=True)
    else:
        return jsonify(success=False, error="Invalid or expired OTP")

# ================= DRAWINGS =================
@app.route('/save_drawings', methods=['POST'])
def save_drawings():
    data = request.get_json()
    os.makedirs(os.path.dirname(DRAWINGS_FILE), exist_ok=True)
    with open(DRAWINGS_FILE, 'w') as f:
        json.dump(data, f)
    return jsonify(success=True)

# ================= PATHFINDING =================
@app.route('/compute_path')
def compute_path():
    if 'user' not in session:
        return jsonify(error="Login required")

    try:
        start_lat = float(request.args.get('start_lat'))
        start_lon = float(request.args.get('start_lon'))
        goal_lat = float(request.args.get('goal_lat'))
        goal_lon = float(request.args.get('goal_lon'))

        start = (start_lat, start_lon)
        goal = (goal_lat, goal_lon)

        load_obstacles()
        path = dstar.compute_path(start, goal)
        return jsonify(path)
    except Exception as e:
        return jsonify(error=str(e))

# ================= TILE BOUNDS =================
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
        return math.degrees(math.atan(math.sinh(n)))

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

# ================= RUN SERVER =================
if __name__ == "__main__":
    app.run(debug=True)
