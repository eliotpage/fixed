import heapq
import numpy as np
import rasterio
from pyproj import Transformer
from PIL import Image
import os
from scipy.ndimage import distance_transform_edt
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import nearest_points


class DStarLite:
    """ D* Lite pathfinder with DEM and cost map. Uses road/water tiles to guide paths and avoid obstacles. """
    
    def __init__(self, dem_path, tile_dir=None, zoom=11):
        # Load DEM (Digital Elevation Model)
        self.dem = rasterio.open(dem_path)
        self.nodata = self.dem.nodata
        self.elev = self.dem.read(1)
        self.rows, self.cols = self.elev.shape

        # CRS transformers
        self.dem_to_wgs84 = Transformer.from_crs(self.dem.crs, "EPSG:4326", always_xy=True)
        self.wgs84_to_dem = Transformer.from_crs("EPSG:4326", self.dem.crs, always_xy=True)

        # Default cost map: all 1 (traversable)
        self.cost_map = np.ones_like(self.elev, dtype=float)

        # Hostile mask and distance slope
        self.hostile_mask = np.zeros_like(self.elev, dtype=bool)

        # If tiles provided, build cost map from roads/water
        if tile_dir:
            self.build_cost_map_from_tiles(tile_dir, zoom)

    # ================= Helper functions =================
    def latlon_to_index(self, lat, lon):
        """ Converts latitude and longitude to DEM row and column indices. """
        x, y = self.wgs84_to_dem.transform(lon, lat)
        col = int((x - self.dem.bounds.left) / self.dem.res[0])
        row = int((self.dem.bounds.top - y) / self.dem.res[1])
        return row, col

    def index_to_latlon(self, row, col):
        """ Converts DEM row and column indices to latitude and longitude. """
        x = self.dem.bounds.left + col * self.dem.res[0]
        y = self.dem.bounds.top - row * self.dem.res[1]
        lon, lat = self.dem_to_wgs84.transform(x, y)
        return lat, lon

    def in_bounds(self, r, c):
        """ Checks if a row and column index is within the bounds of the DEM. """
        return 0 <= r < self.rows and 0 <= c < self.cols

    def neighbors(self, r, c, corridor=None):
        """ Returns the valid neighbors for a given cell, optionally within a corridor. """
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if not self.in_bounds(nr, nc):
                    continue
                if corridor:
                    min_r, max_r, min_c, max_c = corridor
                    if not (min_r <= nr <= max_r and min_c <= nc <= max_c):
                        continue
                yield nr, nc

    def cost(self, r1, c1, r2, c2):
        """ Returns the cost to move from (r1, c1) to (r2, c2). """
        if self.cost_map[r2, c2] <= 0:
            return float('inf')
        elev1 = self.elev[r1, c1] if self.elev[r1, c1] != self.nodata else 0
        elev2 = self.elev[r2, c2] if self.elev[r2, c2] != self.nodata else 0
        slope = abs(elev2 - elev1)
        dist = np.hypot(r2 - r1, c2 - c1)
        return (dist + slope) * self.cost_map[r2, c2]

    def heuristic(self, r1, c1, r2, c2):
        """ Heuristic function for the A* algorithm (straight-line distance). """
        return np.hypot(r2 - r1, c2 - c1)

    # ================= Tile-based cost map =================
    def build_cost_map_from_tiles(self, tile_dir, zoom):
        """ Builds a cost map from road and water tiles. """
        cost = np.ones_like(self.elev, dtype=float) * 2
        tile_size = 256
        for x_tile in os.listdir(os.path.join(tile_dir, str(zoom))):
            x_path = os.path.join(tile_dir, str(zoom), x_tile)
            for y_file in os.listdir(x_path):
                if not y_file.endswith(".png"):
                    continue
                y_tile = int(y_file.split('.')[0])
                tile_path = os.path.join(x_path, y_file)
                tile_img = np.array(Image.open(tile_path).convert("RGB"))
                water = (tile_img[:, :, 2] > 150) & (tile_img[:, :, 0] < 100) & (tile_img[:, :, 1] < 100)
                road = (tile_img.mean(axis=2) > 200)

                r_start = int(y_tile * tile_size * self.rows / (2 ** zoom * tile_size))
                c_start = int(int(x_tile) * tile_size * self.cols / (2 ** zoom * tile_size))
                r_end = min(r_start + tile_size, self.rows)
                c_end = min(c_start + tile_size, self.cols)

                cost[r_start:r_end, c_start:c_end][road[:r_end - r_start, :c_end - c_start]] = 1
                cost[r_start:r_end, c_start:c_end][water[:r_end - r_start, :c_end - c_start]] = 0

        self.cost_map = cost

    # ================== HOSTILE ZONES =================
    def apply_hostile_zones(self, hostile_features, influence_radius_m=100, cost_multiplier=10):
        """ Rasterizes hostile shapes as impassable. Distance-based cost slope starts from the nearest point. """
        self.hostile_mask = np.zeros_like(self.elev, dtype=bool)
        for f in hostile_features:
            geom = None
            if f['geometry']['type'] == 'Point':
                geom = Point(f['geometry']['coordinates'][0], f['geometry']['coordinates'][1])
            elif f['geometry']['type'] == 'Polygon':
                geom = Polygon(f['geometry']['coordinates'][0])
            elif f['geometry']['type'] == 'LineString':
                geom = LineString(f['geometry']['coordinates'])
            else:
                continue

            # Rasterize shape
            min_row, min_col, max_row, max_col = self.rows, self.cols, 0, 0
            if geom.geom_type == 'Point':
                row, col = self.latlon_to_index(geom.y, geom.x)
                if self.in_bounds(row, col):
                    self.hostile_mask[row, col] = True
            else:
                # Iterate DEM grid and mark cells inside polygon or on lines
                for r in range(self.rows):
                    for c in range(self.cols):
                        lat, lon = self.index_to_latlon(r, c)
                        cell_point = Point(lon, lat)
                        if geom.geom_type == 'Polygon' and geom.contains(cell_point):
                            self.hostile_mask[r, c] = True
                        elif geom.geom_type == 'LineString':
                            nearest = nearest_points(geom, cell_point)[0]
                            dist_m = self.latlon_distance(lat, lon, nearest.y, nearest.x)
                            if dist_m < 1:  # <1 meter threshold
                                self.hostile_mask[r, c] = True

        # Impassable
        self.cost_map[self.hostile_mask] = 0

        # Distance-based slope
        inv_mask = ~self.hostile_mask
        distance_cells = distance_transform_edt(inv_mask)
        meters_per_pixel = np.mean(self.dem.res) * 111000
        distance_m = distance_cells * meters_per_pixel
        self.cost_map += np.clip((influence_radius_m - distance_m) / influence_radius_m * cost_multiplier, 0, cost_multiplier)

    def latlon_distance(self, lat1, lon1, lat2, lon2):
        """ Haversine formula to calculate distance between two lat/lon points. """
        R = 6371000  # Radius of the Earth in meters
        dLat = np.radians(lat2 - lat1)
        dLon = np.radians(lon2 - lon1)
        a = np.sin(dLat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dLon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return R * c

    # ===================== Main Pathfinding =================
    def compute_path(self, start, goal, corridor_m=None, debug=False):
        debug_msgs = []
        start_r, start_c = self.latlon_to_index(*start)
        goal_r, goal_c = self.latlon_to_index(*goal)

        if debug:
            debug_msgs.append(f"Start indices: {start_r},{start_c}")
            debug_msgs.append(f"Goal indices: {goal_r},{goal_c}")

        meters_per_pixel = np.mean(self.dem.res) * 111000  # Conversion factor to meters
        corridor_cells = int(corridor_m / meters_per_pixel) if corridor_m else 0

        # Define the bounds of the search corridor (inflated by the corridor distance in cells)
        min_r = max(0, min(start_r, goal_r) - corridor_cells)
        max_r = min(self.rows - 1, max(start_r, goal_r) + corridor_cells)
        min_c = max(0, min(start_c, goal_c) - corridor_cells)
        max_c = min(self.cols - 1, max(start_c, goal_c) + corridor_cells)

        if debug:
            debug_msgs.append(f"Corridor bounds (inflated by {corridor_m} m): {(min_r, max_r, min_c, max_c)}")

        # A* algorithm setup
        frontier = []
        heapq.heappush(frontier, (0, (start_r, start_c)))
        came_from = {(start_r, start_c): None}
        cost_so_far = {(start_r, start_c): 0}
        steps = 0

        while frontier:
            steps += 1
            priority, (r, c) = heapq.heappop(frontier)

            if (r, c) == (goal_r, goal_c):
                if debug:
                    debug_msgs.append(f"Goal reached in {steps} steps")
                break

            for nr, nc in self.neighbors(r, c, corridor=(min_r, max_r, min_c, max_c)):
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