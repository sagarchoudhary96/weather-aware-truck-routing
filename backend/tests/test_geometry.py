import pytest

from planner.domain.geometry import (
    METERS_PER_MILE,
    route_with_timings_from_segments,
    checkpoint_distances_from_start_m,
    road_length_covered_by_each_checkpoint,
    straight_line_distance_m,
    reduce_points_for_drawing,
)

MI = METERS_PER_MILE


def test_straight_line_distance_one_degree_latitude():
    assert straight_line_distance_m((40, -100), (41, -100)) == pytest.approx(111_195, rel=1e-3)


def test_checkpoints_include_origin_and_destination():
    assert checkpoint_distances_from_start_m(100 * MI, 25 * MI) == pytest.approx([0, 25 * MI, 50 * MI, 75 * MI, 100 * MI])
    assert checkpoint_distances_from_start_m(90 * MI, 25 * MI) == pytest.approx([0, 25 * MI, 50 * MI, 75 * MI, 90 * MI])
    assert checkpoint_distances_from_start_m(8 * MI, 10 * MI) == pytest.approx([0, 8 * MI])


def test_coverage_splits_halfway_and_sums_to_length():
    assert road_length_covered_by_each_checkpoint([0, 25, 50, 75, 100]) == [12.5, 25, 25, 25, 12.5]
    assert road_length_covered_by_each_checkpoint([0, 25, 50, 75, 90]) == [12.5, 25, 25, 20, 7.5]
    assert sum(road_length_covered_by_each_checkpoint([0, 10, 20, 23])) == 23


def test_route_timings_spread_segment_durations_by_distance():
    # Three vertices on a meridian, equally spaced; span 1 is slow, span 2 fast.
    coords = [(40.0, -100.0), (40.1, -100.0), (40.2, -100.0), (40.3, -100.0)]
    route_timings = route_with_timings_from_segments(coords, segment_starts=[0, 2], segment_durations=[600, 100])
    assert route_timings.drive_s == pytest.approx([0, 300, 600, 700])

    (lat, _), t = route_timings.position_and_drive_time_at(route_timings.total_m / 2)
    assert lat == pytest.approx(40.15)
    assert t == pytest.approx(450)

    (lat, _), d = route_timings.position_and_distance_after(650)
    assert lat == pytest.approx(40.25)
    assert d == pytest.approx(route_timings.total_m * 2.5 / 3)


def test_route_timings_clamp_outside_range():
    route_timings = route_with_timings_from_segments([(40.0, -100.0), (40.1, -100.0)], [0], [60])
    assert route_timings.position_and_drive_time_at(-5)[1] == 0
    assert route_timings.position_and_drive_time_at(1e9)[1] == 60


def test_simplify_drops_collinear_points_keeps_corners():
    line = [(40.0, -100.0), (40.05, -100.0), (40.1, -100.0), (40.1, -99.9)]
    assert reduce_points_for_drawing(line, tolerance_m=10) == [(40.0, -100.0), (40.1, -100.0), (40.1, -99.9)]
