import math
import os
import requests

# Tile provider
TILE_URL = "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
SUBDOMAINS = ["a", "b", "c"]

# Zoom levels
MIN_ZOOM = 10
MAX_ZOOM = 18

# Bounding box
MIN_LAT = 34.8
MAX_LAT = 35.3
MIN_LON = 32.7
MAX_LON = 33.3

OUT_DIR = "tiles"

# ============================
def latlon_to_tile(lat, lon, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    lat_rad = math.radians(lat)
    y = int(
        (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi)
        / 2 * n
    )
    return x, y

os.makedirs(OUT_DIR, exist_ok=True)
session = requests.Session()

for z in range(MIN_ZOOM, MAX_ZOOM + 1):
    x_min, y_max = latlon_to_tile(MIN_LAT, MIN_LON, z)
    x_max, y_min = latlon_to_tile(MAX_LAT, MAX_LON, z)
    print(f"Zoom {z}: X {x_min}-{x_max}, Y {y_min}-{y_max}")

    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            sub = SUBDOMAINS[(x + y) % len(SUBDOMAINS)]
            url = TILE_URL.format(s=sub, z=z, x=x, y=y)
            folder = f"{OUT_DIR}/{z}/{x}"
            os.makedirs(folder, exist_ok=True)
            filename = f"{folder}/{y}.png"

            if os.path.exists(filename):
                continue

            try:
                r = session.get(url, timeout=15)
                if r.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(r.content)
                    print("Saved", filename)
                else:
                    print("Failed", url, r.status_code)
            except Exception as e:
                print("Error", url, e)
