import heapq
import numpy as np
import rasterio
from pyproj import Transformer
from PIL import Image
import os

class DStarLite:
    """
    D* Lite pathfinder with DEM and cost map.
    Uses road/water tiles to guide paths and avoid obstacles.
    """

    def __init__(self, dem_path, tile_dir=None, zoom=11):
        # Load DEM
        self.dem = rasterio.open(dem_path)
        self.nodata = self.dem.nodata
        self.elev = self.dem.read(1)
        self.rows, self.cols = self.elev.shape

        # CRS transformers
        self.dem_to_wgs84 = Transformer.from_crs(self.dem.crs, "EPSG:4326", always_xy=True)
        self.wgs84_to_dem = Transformer.from_crs("EPSG:4326", self.dem.crs, always_xy=True)

        # Default cost map: all 1 (traversable)
        self.cost_map = np.ones_like(self.elev, dtype=float)

        # If tiles provided, build cost map from roads/water
        if tile_dir:
            self.build_cost_map_from_tiles(tile_dir, zoom)

    # ================= Helper functions =================
    def latlon_to_index(self, lat, lon):
        x, y = self.wgs84_to_dem.transform(lon, lat)
        col = int((x - self.dem.bounds.left) / self.dem.res[0])
        row = int((self.dem.bounds.top - y) / self.dem.res[1])
        return row, col

    def index_to_latlon(self, row, col):
        x = self.dem.bounds.left + col * self.dem.res[0]
        y = self.dem.bounds.top - row * self.dem.res[1]
        lon, lat = self.dem_to_wgs84.transform(x, y)
        return lat, lon

    def in_bounds(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def neighbors(self, r, c, corridor=None):
        for dr in [-1,0,1]:
            for dc in [-1,0,1]:
                if dr==0 and dc==0: continue
                nr, nc = r+dr, c+dc
                if not self.in_bounds(nr, nc): continue
                if corridor:
                    min_r, max_r, min_c, max_c = corridor
                    if not (min_r <= nr <= max_r and min_c <= nc <= max_c): continue
                yield nr, nc

    def cost(self, r1, c1, r2, c2):
        # Blocked areas
        if self.cost_map[r2, c2] <= 0:
            return float('inf')
        # Elevation difference
        elev1 = self.elev[r1, c1] if self.elev[r1, c1] != self.nodata else 0
        elev2 = self.elev[r2, c2] if self.elev[r2, c2] != self.nodata else 0
        slope = abs(elev2 - elev1)
        dist = np.hypot(r2 - r1, c2 - c1)
        return (dist + slope) * self.cost_map[r2, c2]

    def heuristic(self, r1, c1, r2, c2):
        return np.hypot(r2 - r1, c2 - c1)

    # ================= Tile-based cost map =================
    def build_cost_map_from_tiles(self, tile_dir, zoom):
        """
        Create a cost map from road/water tiles.
        Roads = low cost (1), water = 0 (blocked), other = medium (2)
        """
        cost = np.ones_like(self.elev, dtype=float) * 2  # default medium cost
        tile_size = 256  # assume 256x256 px tiles
        for x_tile in os.listdir(os.path.join(tile_dir, str(zoom))):
            x_path = os.path.join(tile_dir, str(zoom), x_tile)
            for y_file in os.listdir(x_path):
                if not y_file.endswith(".png"): continue
                y_tile = int(y_file.split('.')[0])
                tile_path = os.path.join(x_path, y_file)
                tile_img = np.array(Image.open(tile_path).convert("RGB"))

                # Simple detection: blue=water, white/gray=road
                water = (tile_img[:,:,2] > 150) & (tile_img[:,:,0] < 100) & (tile_img[:,:,1] < 100)
                road = (tile_img.mean(axis=2) > 200)

                # Map to DEM indices (rough)
                r_start = int(y_tile * tile_size * self.rows / (2**zoom * tile_size))
                c_start = int(int(x_tile) * tile_size * self.cols / (2**zoom * tile_size))
                r_end = min(r_start + tile_size, self.rows)
                c_end = min(c_start + tile_size, self.cols)

                cost[r_start:r_end, c_start:c_end][road[:r_end-r_start, :c_end-c_start]] = 1
                cost[r_start:r_end, c_start:c_end][water[:r_end-r_start, :c_end-c_start]] = 0
        self.cost_map = cost

    # ================= Main Pathfinding =================
    def compute_path(self, start, goal, corridor_m=None, debug=False):
        debug_msgs = []
        start_r, start_c = self.latlon_to_index(*start)
        goal_r, goal_c = self.latlon_to_index(*goal)

        if debug:
            debug_msgs.append(f"Start indices: {start_r},{start_c}")
            debug_msgs.append(f"Goal indices: {goal_r},{goal_c}")

        # Corridor bounds
        if corridor_m:
            meters_per_pixel = np.mean(self.dem.res) * 111000
            corridor_cells = int(corridor_m / meters_per_pixel)
            min_r = max(0, min(start_r, goal_r) - corridor_cells)
            max_r = min(self.rows-1, max(start_r, goal_r) + corridor_cells)
            min_c = max(0, min(start_c, goal_c) - corridor_cells)
            max_c = min(self.cols-1, max(start_c, goal_c) + corridor_cells)
            corridor = (min_r, max_r, min_c, max_c)
            if debug:
                debug_msgs.append(f"Corridor bounds: {corridor}")
        else:
            corridor = None

        # A* search
        frontier = []
        heapq.heappush(frontier, (0, (start_r, start_c)))
        came_from = {(start_r, start_c): None}
        cost_so_far = {(start_r, start_c): 0}
        steps = 0

        while frontier:
            steps += 1
            priority, (r, c) = heapq.heappop(frontier)
            if (r, c) == (goal_r, goal_c):
                if debug: debug_msgs.append(f"Goal reached in {steps} steps")
                break
            for nr, nc in self.neighbors(r, c, corridor):
                new_cost = cost_so_far[(r, c)] + self.cost(r, c, nr, nc)
                if (nr, nc) not in cost_so_far or new_cost < cost_so_far[(nr, nc)]:
                    cost_so_far[(nr, nc)] = new_cost
                    heapq.heappush(frontier, (new_cost + self.heuristic(nr, nc, goal_r, goal_c), (nr, nc)))
                    came_from[(nr, nc)] = (r, c)
            if debug and steps % 1000 == 0:
                debug_msgs.append(f"Step {steps}, frontier size {len(frontier)}")

        # Reconstruct path
        path = []
        current = (goal_r, goal_c)
        while current in came_from:
            path.append(self.index_to_latlon(*current))
            current = came_from.get(current)
        path.reverse()

        if debug:
            debug_msgs.append(f"Path length: {len(path)}")
            return path, debug_msgs
        return path
