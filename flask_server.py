from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import json
import math

app = Flask(__name__)

# Path to tiles and drawings
TILES_DIR = "static/tiles"
DRAWINGS_FILE = "static/drawings.json"

MIN_ZOOM = 10
MAX_ZOOM = 16

def load_drawings():
    if os.path.exists(DRAWINGS_FILE):
        with open(DRAWINGS_FILE) as f:
            return json.load(f)
    return []

def tile_to_lon(x, z):
    return x / (2**z) * 360.0 - 180.0

def tile_to_lat(y, z):
    n = math.pi - 2.0 * math.pi * y / (2**z)
    return math.degrees(math.atan(math.sinh(n)))

def compute_bounds_all_zoom():
    min_lat, max_lat = 90, -90
    min_lon, max_lon = 180, -180

    for z_name in os.listdir(TILES_DIR):
        z_dir = os.path.join(TILES_DIR, z_name)
        if not os.path.isdir(z_dir): continue
        z = int(z_name)
        for x_name in os.listdir(z_dir):
            x_dir = os.path.join(z_dir, x_name)
            if not os.path.isdir(x_dir): continue
            x_tile = int(x_name)
            for y_file in os.listdir(x_dir):
                if not y_file.endswith(".png"): continue
                y_tile = int(y_file.split(".")[0])
                lon = tile_to_lon(x_tile, z)
                lat = tile_to_lat(y_tile, z)
                min_lat = min(min_lat, lat)
                max_lat = max(max_lat, lat)
                min_lon = min(min_lon, lon)
                max_lon = max(max_lon, lon)

    return {"north": max_lat, "south": min_lat, "west": min_lon, "east": max_lon}

@app.route("/")
def index():
    bounds = compute_bounds_all_zoom()
    return render_template(
        "index.html",
        bounds=bounds,
        min_zoom=MIN_ZOOM,
        max_zoom=MAX_ZOOM,
        drawings=load_drawings()
    )

@app.route("/save_drawings", methods=["POST"])
def save_drawings():
    data = request.get_json()
    with open(DRAWINGS_FILE, "w") as f:
        json.dump(data, f)
    return "ok"

# Example pathfinding endpoint
@app.route("/compute_path")
def compute_path():
    try:
        start_lat = float(request.args["start_lat"])
        start_lon = float(request.args["start_lon"])
        goal_lat = float(request.args["goal_lat"])
        goal_lon = float(request.args["goal_lon"])
    except:
        return jsonify({"error": "Invalid coordinates"}), 400

    # Replace this with your real pathfinding logic
    path = [
        [start_lat, start_lon],
        [goal_lat, goal_lon]
    ]
    return jsonify(path)

if __name__ == "__main__":
    app.run(debug=True)
