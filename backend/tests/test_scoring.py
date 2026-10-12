import pytest

from planner.domain.models import RiskLevel
from planner.domain.scoring import rank_routes, summarize_route_risk

L, M, H, S, NT = RiskLevel
HOUR = 3600
NAMES = {"A": "Route A", "B": "Route B", "C": "Route C"}


def route(route_id, levels, miles, hours):
    return summarize_route_risk(route_id, sum(miles), hours * HOUR, levels, miles)


def test_summary_miles_and_distance_weighted_average():
    s = route("A", [L, M, S, M, L], [12.5, 25, 25, 25, 12.5], 2)
    assert s.severe_mi == 25 and s.high_mi == 0
    assert s.miles_by_level[M] == 50
    assert s.avg_risk == pytest.approx(1.25)
    assert s.max_level == S and not s.disqualified


def test_unknown_miles_excluded_from_average():
    s = route("A", [H, None], [10, 10], 1)
    assert s.unknown_mi == 10
    assert s.avg_risk == 2


def test_severe_then_high_beats_travel_time():
    a = route("A", [S, L], [25, 75], 9)  # fastest but has Severe miles
    b = route("B", [H, L], [50, 50], 10)
    c = route("C", [H, L], [25, 75], 11)  # slowest, fewest High miles
    result = rank_routes([a, b, c], NAMES)
    assert result.order == ["C", "B", "A"]
    assert result.recommended_id == "C"
    assert result.explanations["C"] == "Recommended: fewer High miles than Route B (25 mi vs 50 mi)."
    assert result.explanations["A"] == "Ranked below Route C: more Severe miles (25 mi vs 0 mi)."


def test_average_risk_then_travel_time_break_ties():
    a = route("A", [M, L], [50, 50], 9)
    b = route("B", [M, L], [20, 80], 10)
    c = route("C", [M, L], [20, 80], 8)
    result = rank_routes([a, b, c], NAMES)
    assert result.order == ["C", "B", "A"]
    assert "shorter travel time" in result.explanations["C"]
    assert result.explanations["A"] == "Ranked below Route C: higher average risk (0.50 vs 0.20), with 50 mi of Moderate vs 20 mi."


def test_no_travel_disqualifies_even_if_otherwise_best():
    a = route("A", [NT, L], [1, 99], 5)
    b = route("B", [S, L], [50, 50], 12)
    result = rank_routes([a, b], NAMES)
    assert result.order == ["B", "A"]
    assert result.recommended_id == "B"
    assert result.explanations["A"] == "Not recommended: 1 mi in No Travel conditions."


def test_all_disqualified_has_no_recommendation_but_is_ranked():
    a = route("A", [NT, L], [30, 70], 5)
    b = route("B", [NT, L], [10, 90], 6)
    result = rank_routes([a, b], NAMES)
    assert result.recommended_id is None
    assert result.order == ["B", "A"]


def test_float_noise_does_not_decide():
    a = route("A", [H, L], [25.000001, 74.999999], 10)
    b = route("B", [H, L], [25.0, 75.0], 9)
    assert rank_routes([a, b], NAMES).order == ["B", "A"]  # equal High miles → faster wins
