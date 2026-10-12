from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from django.core.cache import cache

from planner.providers.errors import NoRouteError, ProviderError
from planner.providers.tomtom import TomTomClient, gross_vehicle_weight_kg, parse_route_with_timings

ROUTE_PATTERN = r"https://api\.tomtom\.com/routing/1/calculateRoute/.*"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def points(*lats):
    return [{"latitude": lat, "longitude": -100.0} for lat in lats]


def route(legs, instructions, total_s):
    return {
        "summary": {"travelTimeInSeconds": total_s, "lengthInMeters": 1000},
        "legs": [{"points": p} for p in legs],
        "guidance": {"instructions": instructions},
    }


def ins(index, seconds):
    return {"pointIndex": index, "travelTimeInSeconds": seconds}


def test_gross_weight_adds_tare_and_converts_to_kg():
    assert gross_vehicle_weight_kg(45_000) == round(80_000 * 0.45359237)


def test_instruction_times_become_vertex_times():
    r = route([points(40.0, 40.1, 40.2, 40.3)], [ins(0, 0), ins(2, 400), ins(3, 450)], 450)
    assert parse_route_with_timings(r).route_timings.drive_s == pytest.approx([0, 200, 400, 450])


def test_missing_final_instruction_uses_summary_total():
    r = route([points(40.0, 40.1, 40.2)], [ins(0, 0)], 600)
    assert parse_route_with_timings(r).route_timings.drive_s == pytest.approx([0, 300, 600])


def test_legs_are_concatenated_and_duplicate_indices_ignored():
    # Point indices count across all legs; the via point repeats as the next leg's first point.
    r = route(
        [points(40.0, 40.1), points(40.1, 40.2)],
        [ins(0, 0), ins(2, 100), ins(2, 100), ins(3, 300)],
        300,
    )
    route_timings = parse_route_with_timings(r).route_timings
    assert len(route_timings.lats) == 4
    assert route_timings.drive_s == pytest.approx([0, 100, 100, 300])


@respx.mock
def test_routes_request_parameters():
    mock = respx.get(url__regex=ROUTE_PATTERN).mock(
        return_value=httpx.Response(200, json={"routes": [route([points(40.0, 40.1)], [ins(0, 0), ins(1, 60)], 60)]})
    )
    departure = datetime.now(UTC) + timedelta(hours=2)
    TomTomClient("key", httpx.Client()).fetch_truck_routes((40, -100), (40.1, -100), departure, 20_000, alternatives=2, via=(40.05, -99.9))
    request = mock.calls[0].request
    assert "40,-100:40.05,-99.9:40.1,-100" in request.url.path
    params = request.url.params
    assert params["travelMode"] == "truck"
    assert params["maxAlternatives"] == "2"
    assert params["vehicleWeight"] == str(gross_vehicle_weight_kg(20_000))
    assert params["departAt"].startswith(departure.date().isoformat())

    TomTomClient("key", httpx.Client()).fetch_truck_routes((40, -100), (40.1, -100), departure, 20_000, alternatives=2, via=(40.05, -99.9))
    assert mock.call_count == 1  # identical request served from cache


@respx.mock
def test_errors():
    client = TomTomClient("key", httpx.Client())
    respx.get(url__regex=ROUTE_PATTERN).mock(return_value=httpx.Response(403, json={}))
    with pytest.raises(ProviderError, match="API key"):
        client.fetch_truck_routes((40, -100), (41, -100), datetime.now(UTC), 0)

    respx.get(url__regex=ROUTE_PATTERN).mock(
        return_value=httpx.Response(400, json={"detailedError": {"code": "NO_ROUTE_FOUND", "message": "NO_ROUTE_FOUND"}})
    )
    with pytest.raises(NoRouteError):
        client.fetch_truck_routes((40, -100), (41, -100), datetime.now(UTC), 0)
