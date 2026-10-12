"""End-to-end API tests with fake routing and weather providers."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from planner import providers
from planner.domain.geometry import route_with_timings_from_known_times
from planner.providers.tomtom import TruckRoute
from planner.providers.open_meteo import HourlyForecast

HOUR = 3600
ORIGIN, DEST = (40.0, -100.0), (40.0, -90.0)


def straight_route(mid_lat: float, hours: float) -> TruckRoute:
    coords = [ORIGIN, (mid_lat, -95.0), DEST]
    return TruckRoute(route_with_timings_from_known_times(coords, {0: 0, 2: hours * HOUR}))


class FakeRouting:
    """Returns two routes for the main call so the detour fallback supplies the third."""

    def __init__(self):
        self.calls = []

    def fetch_truck_routes(self, origin, destination, departure, load_lb, alternatives=0, via=None):
        self.calls.append(via)
        if via is None:
            return [straight_route(40.0, 9), straight_route(42.0, 10)]
        return [straight_route(38.0 if via[0] < 40 else 42.0, 12)]


class FakeWeather:
    """Strong wind north of 41°N, calm elsewhere."""

    def fetch_hourly_forecasts(self, points, start, end):
        first = int(start.timestamp()) // HOUR * HOUR
        hours = int((end - start).total_seconds() // HOUR) + 3
        return [
            HourlyForecast(first, [50.0 if lat > 41 else 10.0] * hours, [None] * hours, [0.0] * hours, [0.0] * hours)
            for lat, _ in points
        ]


@pytest.fixture
def client(monkeypatch):
    routing = FakeRouting()
    monkeypatch.setattr(providers, "routing_client", lambda: routing)
    monkeypatch.setattr(providers, "weather_client", lambda: FakeWeather())
    return APIClient()


def payload(**overrides):
    body = {
        "origin": {"lat": ORIGIN[0], "lon": ORIGIN[1]},
        "destination": {"lat": DEST[0], "lon": DEST[1]},
        "departure": (timezone.now() + timedelta(hours=1)).isoformat(),
        "load_lb": 35_000,
        "interval_mi": 25,
    }
    return {**body, **overrides}


def test_plan_ranks_routes_and_disqualifies_windy_one(client):
    res = client.post("/api/plan/", payload(), format="json")
    assert res.status_code == 200, res.json()
    data = res.json()
    routes = data["routes"]
    assert [r["id"] for r in routes] == ["A", "C", "B"]
    assert data["recommended_id"] == "A"
    assert routes[2]["summary"]["disqualified"]  # 50 mph + 35,000 lb → No Travel
    assert routes[1]["generated"]
    assert routes[1]["explanation"].startswith("Ranked below Route A: longer travel time")


def test_checkpoints_cover_route_and_include_breaks(client):
    route = client.post("/api/plan/", payload(), format="json").json()["routes"][0]
    cps = route["checkpoints"]
    assert cps[0]["mile"] == 0 and cps[-1]["mile"] == route["distance_mi"]
    assert sum(c["covered_mi"] for c in cps) == pytest.approx(route["distance_mi"], abs=0.1)
    assert [s["kind"] for s in route["stops"]] == ["break"]  # 9 h of driving
    assert route["trip_s"] == 9.5 * HOUR


def test_line_ranges_split_the_geometry_into_checkpoint_pieces(client):
    for route in client.post("/api/plan/", payload(), format="json").json()["routes"]:
        ranges = [cp["line_range"] for cp in route["checkpoints"]]
        assert ranges[0][0] == 0 and ranges[-1][1] == len(route["geometry"]) - 1
        assert all(prev[1] == nxt[0] for prev, nxt in zip(ranges, ranges[1:]))  # pieces join end to end


def test_hos_can_be_disabled(client):
    route = client.post("/api/plan/", payload(apply_hos=False), format="json").json()["routes"][0]
    assert route["stops"] == [] and route["trip_s"] == 9 * HOUR


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"departure": (timezone.now() - timedelta(hours=3)).isoformat()}, "departure"),
        ({"departure": (timezone.now() + timedelta(days=9)).isoformat()}, "departure"),
        ({"load_lb": 90_000}, "load_lb"),
        ({"interval_mi": 30}, "interval_mi"),
        ({"destination": {"lat": ORIGIN[0], "lon": ORIGIN[1]}}, "non_field_errors"),
    ],
)
def test_validation(client, overrides, field):
    res = client.post("/api/plan/", payload(**overrides), format="json")
    assert res.status_code == 400
    assert field in res.json()


def test_heatmap_returns_hourly_risk_per_point(client):
    body = {
        "routes": [[[ORIGIN[1], ORIGIN[0]], [-95.0, 42.0], [DEST[1], DEST[0]]]],
        "departure": (timezone.now() + timedelta(hours=1)).isoformat(),
        "load_lb": 35_000,
    }
    res = client.post("/api/heatmap/", body, format="json")
    assert res.status_code == 200, res.json()
    data = res.json()
    assert data["hours"] == 48
    assert len(data["risk"]) == len(data["points"]) > 0
    assert data["cell_deg"][0] > 0 and data["cell_deg"][1] > data["cell_deg"][0]  # lon degrees are shorter
    assert all(len(row) == 49 for row in data["risk"])
    levels = {v for row in data["risk"] for v in row}
    assert levels <= {0, 4}  # calm or No Travel in this fake weather
