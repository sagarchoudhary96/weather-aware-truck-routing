"""Where does the heatmap sample the weather? Evenly spaced grid cells within 40 km of any route.

Each cell needs one forecast lookup, so the count is capped at 350: cells are at least 12 km
apart and spread out further on long trips. Example: Chicago → Denver gives ~270 cells about
22 km apart.
"""

import math
from dataclasses import dataclass

from .geometry import Coord, distance_from_start_at_each_point_m, straight_line_distance_m, evenly_spaced_points_along

CORRIDOR_RADIUS_KM = 40
MIN_SPACING_KM = 12
MAX_POINTS = 350
KM_PER_DEG_LAT = 111.32


@dataclass(frozen=True)
class HeatmapGrid:
    points: list[Coord]  # cell centres
    spacing_km: float
    dlat: float  # cell size in degrees
    dlon: float


def _cell_size_degrees(lines: list[list[Coord]], spacing_km: float) -> tuple[float, float]:
    """Cell size in degrees. A degree of longitude is shorter further north, so dlon > dlat."""
    ref_lat = sum(c[0] for line in lines for c in line) / sum(len(line) for line in lines)
    return spacing_km / KM_PER_DEG_LAT, spacing_km / (KM_PER_DEG_LAT * math.cos(math.radians(ref_lat)))


def _cells_within_radius(lines: list[list[Coord]], spacing_km: float, radius_km: float) -> list[Coord]:
    """Walk along each route and collect every grid cell whose centre is within `radius_km`.

    Cells are on one fixed grid, so overlapping routes share cells instead of duplicating them.
    """
    dlat, dlon = _cell_size_degrees(lines, spacing_km)
    reach_i = math.ceil(radius_km / spacing_km)

    cells: set[tuple[int, int]] = set()
    for line in lines:
        for lat, lon in evenly_spaced_points_along(line, spacing_km * 500):  # samples every half cell
            ci, cj = round(lat / dlat), round(lon / dlon)
            reach_j = math.ceil(radius_km / (dlon * KM_PER_DEG_LAT * math.cos(math.radians(lat))))
            for i in range(ci - reach_i, ci + reach_i + 1):
                for j in range(cj - reach_j, cj + reach_j + 1):
                    if (i, j) not in cells and straight_line_distance_m((lat, lon), (i * dlat, j * dlon)) <= radius_km * 1000:
                        cells.add((i, j))
    return [(i * dlat, j * dlon) for i, j in sorted(cells)]


def heatmap_cells_around_routes(
    lines: list[list[Coord]],
    radius_km: float = CORRIDOR_RADIUS_KM,
    max_points: int = MAX_POINTS,
    min_spacing_km: float = MIN_SPACING_KM,
) -> HeatmapGrid:
    """Grid cell centres around all routes, at most `max_points` of them."""
    # Start from the spacing that would fit the corridor area (ignoring overlap), then widen if needed.
    length_km = sum(distance_from_start_at_each_point_m(line)[-1] for line in lines) / 1000
    area = length_km * 2 * radius_km + math.pi * radius_km**2
    spacing = max(min_spacing_km, math.sqrt(area / max_points))
    while True:
        points = _cells_within_radius(lines, spacing, radius_km)
        if len(points) <= max_points:
            return HeatmapGrid(points, spacing, *_cell_size_degrees(lines, spacing))
        spacing *= 1.15
