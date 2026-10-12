from planner.domain.geometry import straight_line_distance_m, evenly_spaced_points_along
from planner.domain.heatmap_grid import heatmap_cells_around_routes

CHICAGO_TO_DENVER = [(41.88, -87.63), (41.26, -95.94), (39.74, -104.99)]


def test_points_stay_within_corridor():
    grid = heatmap_cells_around_routes([CHICAGO_TO_DENVER], radius_km=40)
    samples = evenly_spaced_points_along(CHICAGO_TO_DENVER, 2000)
    for p in grid.points:
        assert min(straight_line_distance_m(p, s) for s in samples) <= 40_000 + 2_000


def test_point_count_is_capped_and_spacing_widens():
    short = heatmap_cells_around_routes([[(41.88, -87.63), (41.6, -88.1)]], max_points=350)
    long = heatmap_cells_around_routes([CHICAGO_TO_DENVER], max_points=150)
    assert len(long.points) <= 150
    assert long.spacing_km > short.spacing_km


def test_overlapping_routes_share_points():
    one = heatmap_cells_around_routes([CHICAGO_TO_DENVER], max_points=10_000)
    two = heatmap_cells_around_routes([CHICAGO_TO_DENVER, CHICAGO_TO_DENVER], max_points=10_000)
    assert one.points == two.points
