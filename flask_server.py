from flask import Flask, render_template, request, jsonify
import os, json, math

app = Flask(__name__)

DRAWINGS_FILE = os.path.join('static', 'drawings.json')
TILE_DIR = os.path.join('static', 'tiles')

# Serve main page
@app.route('/')
def index():
    return render_template('index.html')

# Serve login page
@app.route('/login')
def login():
    return render_template('login.html')

# Save drawings
@app.route('/save_drawings', methods=['POST'])
def save_drawings():
    data = request.get_json()
    os.makedirs(os.path.dirname(DRAWINGS_FILE), exist_ok=True)
    with open(DRAWINGS_FILE, 'w') as f:
        json.dump(data, f)
    return jsonify(success=True)

# Dummy pathfinding
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

# Detect existing zoom 10 tiles and compute bounds
@app.route('/tile_bounds')
def tile_bounds():
    zoom = 10
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
    east = tile2lon(max_x+1, zoom)
    north = tile2lat(min_y, zoom)
    south = tile2lat(max_y+1, zoom)
    center_lat = (north + south)/2
    center_lon = (west + east)/2

    return jsonify({
        'bounds': [[south, west], [north, east]],
        'center': [center_lat, center_lon],
        'minZoom': 9,
        'maxZoom': 14
    })


if __name__ == "__main__":
    app.run(debug=True)
