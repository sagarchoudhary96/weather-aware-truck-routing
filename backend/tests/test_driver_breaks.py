from planner.domain.driver_breaks import HOUR, DriverBreakPlan


def kinds(break_plan):
    return [(s.kind, s.at_drive_s / HOUR) for s in break_plan.stops]


def test_no_stops_for_short_trip_or_exact_limit():
    assert DriverBreakPlan.for_total_driving_time(5 * HOUR).stops == []
    assert DriverBreakPlan.for_total_driving_time(8 * HOUR).stops == []


def test_break_then_rest_cycles():
    assert kinds(DriverBreakPlan.for_total_driving_time(9 * HOUR)) == [("break", 8)]
    assert kinds(DriverBreakPlan.for_total_driving_time(11 * HOUR)) == [("break", 8)]
    assert kinds(DriverBreakPlan.for_total_driving_time(12 * HOUR)) == [("break", 8), ("rest", 11)]
    assert kinds(DriverBreakPlan.for_total_driving_time(25 * HOUR)) == [("break", 8), ("rest", 11), ("break", 19), ("rest", 22)]


def test_disabled_break_plan_has_no_stops():
    assert DriverBreakPlan.for_total_driving_time(30 * HOUR, apply_hos=False).stops == []


def test_elapsed_time_includes_completed_stops():
    s = DriverBreakPlan.for_total_driving_time(12 * HOUR)
    assert s.trip_clock_after_driving(7 * HOUR) == 7 * HOUR
    assert s.trip_clock_after_driving(8 * HOUR) == 8 * HOUR  # reached just before the break
    assert s.trip_clock_after_driving(9 * HOUR) == 9.5 * HOUR
    assert s.trip_clock_after_driving(12 * HOUR) == 12 * HOUR + 0.5 * HOUR + 10 * HOUR


def test_drive_time_is_constant_while_stopped():
    s = DriverBreakPlan.for_total_driving_time(12 * HOUR)
    assert s.driving_completed_at(8.2 * HOUR) == 8 * HOUR  # on break
    assert s.driving_completed_at(9.5 * HOUR) == 9 * HOUR
    assert s.driving_completed_at(15 * HOUR) == 11 * HOUR  # resting
    assert s.driving_completed_at(22 * HOUR) == 11.5 * HOUR
    for drive in (3, 8.5, 10, 11.7):
        assert s.driving_completed_at(s.trip_clock_after_driving(drive * HOUR)) == drive * HOUR
