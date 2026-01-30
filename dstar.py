class DStar:
    def __init__(self):
        # For simplicity, obstacles are read from drawings marked as "Polygon" or "Circle"
        self.obstacles = []

    def compute_path(self, start, goal):
        """
        Compute path from start to goal.
        Start/goal are (lat, lon) tuples.
        Path avoids obstacles in drawings.
        Returns list of (lat, lon) points.
        """
        # Very simple grid-based example, replace with your actual D* logic
        path = [start]

        # Example: naive straight-line, but skip points inside obstacles
        lat1, lon1 = start
        lat2, lon2 = goal

        # Simple interpolation to generate steps
        steps = 50
        for i in range(1, steps + 1):
            lat = lat1 + (lat2 - lat1) * i / steps
            lon = lon1 + (lon2 - lon1) * i / steps
            if not self.is_in_obstacle((lat, lon)):
                path.append((lat, lon))

        path.append(goal)
        return path

    def is_in_obstacle(self, point):
        """
        Returns True if point (lat, lon) is inside any obstacle.
        Obstacles can be circles or polygons stored in drawings.json
        """
        lat, lon = point
        for obs in self.obstacles:
            geom = obs.get("geometry", {})
            if geom.get("type") == "Polygon":
                from shapely.geometry import Point, Polygon
                poly = Polygon([(c[1], c[0]) for c in geom["coordinates"][0]])
                if poly.contains(Point(lon, lat)):
                    return True
            elif geom.get("type") == "Point" and obs.get("properties", {}).get("radius"):
                from shapely.geometry import Point
                circle_center = obs["geometry"]["coordinates"]
                radius = obs["properties"]["radius"]
                # Haversine distance for more accuracy if needed
                dist = ((lat - circle_center[1])**2 + (lon - circle_center[0])**2)**0.5
                if dist <= radius/111000:  # approx deg from meters
                    return True
        return False
