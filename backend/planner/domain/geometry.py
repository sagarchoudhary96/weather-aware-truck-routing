"""Questions about positions along a route. A route is a list of (lat, lon) points.

1. Distances: how far apart points are, and how far along the route each one is.
2. RouteWithTimings: distance and driving time at every point, so we can ask
   "when does the truck reach mile X?" and "where is it after N hours of driving?".
3. Checkpoints: where they go, and how many miles of road each one stands for.
4. Line helpers: simplify a line for drawing, compare two routes, make detour points.
"""

import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_008.8
METERS_PER_MILE = 1609.344

Coord = tuple[float, float]  # (lat, lon)


def straight_line_distance_m(point_a: Coord, point_b: Coord) -> float:
    """How far apart are two GPS points? Great-circle (haversine) distance.

    Example: (40, -100) → (41, -100) ≈ 111,195 m (one degree of latitude).
    """
    lat1, lon1, lat2, lon2 = map(math.radians, (*point_a, *point_b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def distance_from_start_at_each_point_m(points: list[Coord]) -> list[float]:
    """How far along the route is each point? A running total of the gaps.

    Example: 4 points, 10 km apart → [0, 10000, 20000, 30000].
    """
    distances = [0.0]
    for previous, point in zip(points, points[1:]):
        distances.append(distances[-1] + straight_line_distance_m(previous, point))
    return distances


def _value_between(start: float, end: float, fraction: float) -> float:
    """Example: _value_between(300, 600, 0.5) → 450."""
    return start + (end - start) * fraction


def _values_at_position(positions: list[float], at: float, *series: list[float]) -> tuple[float, ...]:
    """Read every series at position `at`, blending the two nearest rows.

    Example: positions [0, 10, 20], drive [0, 300, 600], at=15 → (450,).
    Values outside the range clamp to the first or last row.
    """
    if at <= positions[0]:
        return tuple(s[0] for s in series)
    if at >= positions[-1]:
        return tuple(s[-1] for s in series)
    i = bisect_right(positions, at) - 1
    gap = positions[i + 1] - positions[i]
    fraction = (at - positions[i]) / gap if gap else 0.0
    return tuple(_value_between(s[i], s[i + 1], fraction) for s in series)


@dataclass(frozen=True)
class RouteWithTimings:
    """A route as a table: one row per point, with distance (m) and driving time (s) from the start.

        point   dist_m    drive_s
        P0           0          0
        P1      10,000        300
        P2      20,000        600
        P3      30,000        700
    """

    lats: list[float]
    lons: list[float]
    dist_m: list[float]
    drive_s: list[float]

    @property
    def coords(self) -> list[Coord]:
        return list(zip(self.lats, self.lons))

    @property
    def total_m(self) -> float:
        return self.dist_m[-1]

    @property
    def total_drive_s(self) -> float:
        return self.drive_s[-1]

    def position_and_drive_time_at(self, distance_m: float) -> tuple[Coord, float]:
        """At `distance_m` along the route, where is the truck and how long has it driven?

        Used for checkpoint ETAs. Example (table above): 15,000 m → between P1 and P2, 450 s.
        """
        lat, lon, drive_s = _values_at_position(self.dist_m, distance_m, self.lats, self.lons, self.drive_s)
        return (lat, lon), drive_s

    def points_between(self, start_m: float, end_m: float) -> list[Coord]:
        """The stretch of route from `start_m` to `end_m`, cut exactly at both ends.

        Used to colour the route by checkpoint risk. Example (table above): 5,000 → 25,000 m
        gives [halfway P0–P1, P1, P2, halfway P2–P3].
        """
        start, _ = self.position_and_drive_time_at(start_m)
        end, _ = self.position_and_drive_time_at(end_m)
        first, last = bisect_right(self.dist_m, start_m), bisect_left(self.dist_m, end_m)
        return [start, *zip(self.lats[first:last], self.lons[first:last]), end]

    def position_and_distance_after(self, drive_s: float) -> tuple[Coord, float]:
        """After `drive_s` seconds of driving, where is the truck and how far has it gone?

        Used for driver stops and the truck on the slider. Example: 650 s → between P2 and P3, 25,000 m.
        """
        lat, lon, distance_m = _values_at_position(self.drive_s, drive_s, self.lats, self.lons, self.dist_m)
        return (lat, lon), distance_m


def route_with_timings_from_known_times(points: list[Coord], seconds_at_point: dict[int, float]) -> RouteWithTimings:
    """Build RouteWithTimings when the driving time is known only at some points, not every point.

    TomTom gives the time from the start at its turn instructions only. Between two known points
    the time is spread in proportion to distance. `seconds_at_point` must include the first and
    last point indices and must not decrease along the route.

    Example: 4 points 10 km apart, {0: 0, 2: 600, 3: 700} → drive_s = [0, 300, 600, 700].
    """
    distances = distance_from_start_at_each_point_m(points)
    drive = [0.0] * len(points)
    known = sorted(seconds_at_point)
    for start, end in zip(known, known[1:]):
        start_s, end_s = seconds_at_point[start], seconds_at_point[end]
        length = distances[end] - distances[start]
        for i in range(start, end + 1):
            share = (distances[i] - distances[start]) / length if length else (i - start) / (end - start)
            drive[i] = start_s + (end_s - start_s) * share
    return RouteWithTimings([p[0] for p in points], [p[1] for p in points], distances, drive)


def checkpoint_distances_from_start_m(total_m: float, interval_m: float) -> list[float]:
    """Where do checkpoints go? Every interval from the origin, plus the destination.

    Example (miles): 90 mi route, 25 mi interval → [0, 25, 50, 75, 90].
    """
    count = int(total_m // interval_m)
    positions = [i * interval_m for i in range(count + 1)]
    if total_m - positions[-1] > 1e-6:
        positions.append(total_m)
    return positions


def coverage_boundaries_m(checkpoint_positions: list[float]) -> list[float]:
    """Where each checkpoint's stretch of road starts and ends. Every point uses its nearest
    checkpoint, so the boundaries fall halfway between neighbours.

    Example (miles): [0, 25, 50, 75, 90] → [0, 12.5, 37.5, 62.5, 82.5, 90].
    """
    first, last = checkpoint_positions[0], checkpoint_positions[-1]
    halfway = ((here + after) / 2 for here, after in zip(checkpoint_positions, checkpoint_positions[1:]))
    return [first, *halfway, last] if len(checkpoint_positions) > 1 else [first, first]


def road_length_covered_by_each_checkpoint(checkpoint_positions: list[float]) -> list[float]:
    """How much road does each checkpoint stand for? The gaps between its coverage boundaries,
    which add up to the route length.

    Example (miles): [0, 25, 50, 75, 90] → [12.5, 25, 25, 20, 7.5].
    """
    boundaries = coverage_boundaries_m(checkpoint_positions)
    return [end - start for start, end in zip(boundaries, boundaries[1:])]


def _to_flat_metres(point: Coord, ref_lat: float) -> tuple[float, float]:
    """Lat/lon → flat (x, y) metres, accurate enough over a few hundred km. Makes the vector maths simple."""
    k = math.pi / 180 * EARTH_RADIUS_M
    return point[1] * k * math.cos(math.radians(ref_lat)), point[0] * k


def distance_from_point_to_segment_m(point: Coord, segment_start: Coord, segment_end: Coord) -> float:
    """How far is a point from the nearest spot on a road segment? Used to compare routes."""
    ref = point[0]
    # Vector maths in flat metres: p = point, a/b = segment ends, d = segment direction.
    (px, py), (ax, ay), (bx, by) = (_to_flat_metres(c, ref) for c in (point, segment_start, segment_end))
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    along = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
    return math.hypot(px - (ax + along * dx), py - (ay + along * dy))


def reduce_points_for_drawing(points: list[Coord], tolerance_m: float) -> list[Coord]:
    """Drop points that sit on almost-straight stretches (Douglas–Peucker simplification).

    A point is kept only if it is more than `tolerance_m` off the line between its neighbours.
    Example: a 1,000-mile route goes from ~10,000 points to ~1,000 at 40 m, with no visible change.
    """
    if len(points) < 3:
        return list(points)
    ref = sum(p[0] for p in points) / len(points)
    xy = [_to_flat_metres(p, ref) for p in points]
    tolerance2 = tolerance_m * tolerance_m
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        (ax, ay), (bx, by) = xy[start], xy[end]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        farthest_i, farthest_d2 = -1, tolerance2
        for i in range(start + 1, end):
            px, py = xy[i]
            along = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
            ex, ey = px - ax - along * dx, py - ay - along * dy
            d2 = ex * ex + ey * ey
            if d2 > farthest_d2:
                farthest_i, farthest_d2 = i, d2
        if farthest_i != -1:
            keep[farthest_i] = True
            stack += [(start, farthest_i), (farthest_i, end)]
    return [p for p, k in zip(points, keep) if k]


def share_of_route_overlapping(
    route: list[Coord], other_route: list[Coord], within_m: float = 2000, samples: int = 60
) -> float:
    """What fraction of `route` runs within `within_m` of `other_route`? (0 to 1)

    Samples 60 points along `route`. Example: two routes sharing the same highway → ~1.0,
    I-80 vs I-70 between Denver and Salt Lake City → near 0. ≥ 0.9 counts as a duplicate.
    """
    length = distance_from_start_at_each_point_m(route)[-1]
    samples_along = evenly_spaced_points_along(route, max(length / samples, 1.0))
    segments = list(zip(other_route, other_route[1:])) or [(other_route[0], other_route[0])]
    near = sum(
        1
        for p in samples_along
        if any(distance_from_point_to_segment_m(p, start, end) <= within_m for start, end in segments)
    )
    return near / len(samples_along)


def detour_waypoints_either_side(origin: Coord, destination: Coord) -> list[Coord]:
    """Two points to the left and right of the trip's midpoint, used to force alternative routes.

    Offset = 20% of the straight-line distance, kept between 30 and 200 km.
    Example: Chicago → Denver (~1,480 km) → points ~200 km north and south of the midpoint.
    """
    straight_km = straight_line_distance_m(origin, destination) / 1000
    offset_km = min(max(0.2 * straight_km, 30), 200)
    mid_lat, mid_lon = (origin[0] + destination[0]) / 2, (origin[1] + destination[1]) / 2
    (ox, oy), (dx, dy) = _to_flat_metres(origin, mid_lat), _to_flat_metres(destination, mid_lat)
    norm = math.hypot(dx - ox, dy - oy) or 1.0
    perp_x, perp_y = -(dy - oy) / norm, (dx - ox) / norm  # unit vector perpendicular to the straight line
    k = math.pi / 180 * EARTH_RADIUS_M
    waypoints = []
    for side in (1, -1):
        dlat = side * perp_y * offset_km * 1000 / k
        dlon = side * perp_x * offset_km * 1000 / (k * math.cos(math.radians(mid_lat)))
        waypoints.append((mid_lat + dlat, mid_lon + dlon))
    return waypoints


def evenly_spaced_points_along(points: list[Coord], spacing_m: float) -> list[Coord]:
    """Points every `spacing_m` along the line, including both ends. Used for route comparison and the heatmap grid."""
    distances = distance_from_start_at_each_point_m(points)
    lats, lons = [p[0] for p in points], [p[1] for p in points]
    positions = checkpoint_distances_from_start_m(distances[-1], spacing_m) if distances[-1] > 0 else [0.0]
    return [_values_at_position(distances, at, lats, lons) for at in positions]
