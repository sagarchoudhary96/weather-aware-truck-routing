from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from django.core.cache import cache

from planner.providers.errors import ProviderError
from planner.providers.open_meteo import URL, HourlyForecast, OpenMeteoClient

T0 = datetime(2026, 10, 13, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def forecast():
    return HourlyForecast(
        start=int(T0.timestamp()),
        wind=[10, 20, 30],
        gust=[15, 25, 35],
        rain=[0.0, 0.2, 0.4],
        snow=[0.0, 0.0, 1.5],
    )


def test_wind_uses_nearest_hour_precip_uses_containing_hour():
    f = forecast()
    w = f.weather_at_time(T0 + timedelta(minutes=10))
    assert (w.wind_mph, w.rain_in_hr) == (10, 0.2)  # 12:10 → wind 12:00, rain total for 12:00–13:00
    w = f.weather_at_time(T0 + timedelta(minutes=40))
    assert (w.wind_mph, w.rain_in_hr) == (20, 0.2)
    w = f.weather_at_time(T0 + timedelta(hours=1))
    assert (w.wind_mph, w.rain_in_hr) == (20, 0.2)


def test_outside_window_is_unknown():
    w = forecast().weather_at_time(T0 + timedelta(hours=5))
    assert w.wind_mph is None and w.rain_in_hr is None


def api_item(lat, lon, wind=12.0, rain=0.05, showers=0.1, snow=0.0):
    return {
        "latitude": lat,
        "longitude": lon,
        "hourly": {
            "time": [int(T0.timestamp()), int(T0.timestamp()) + 3600],
            "wind_speed_10m": [wind, wind],
            "wind_gusts_10m": [wind + 5, wind + 5],
            "rain": [rain, rain],
            "showers": [showers, showers],
            "snowfall": [snow, snow],
        },
    }


@respx.mock
def test_batches_dedupes_sums_showers_and_caches():
    route = respx.get(URL).mock(
        return_value=httpx.Response(200, json=[api_item(41.88, -87.63), api_item(39.74, -104.99, wind=40)])
    )
    client = OpenMeteoClient(httpx.Client())
    points = [(41.881, -87.631), (39.74, -104.99), (41.8812, -87.6309)]  # first and last round together

    result = client.fetch_hourly_forecasts(points, T0, T0 + timedelta(hours=1))
    assert route.call_count == 1
    assert route.calls[0].request.url.params["latitude"].count(",") == 1  # two unique locations
    assert result[0] is result[2]
    assert result[1].wind[0] == 40
    assert result[0].rain[0] == pytest.approx(0.15)  # rain + showers

    client.fetch_hourly_forecasts(points, T0, T0 + timedelta(hours=1))
    assert route.call_count == 1  # served from cache


@respx.mock
def test_error_raises_provider_error():
    respx.get(URL).mock(return_value=httpx.Response(400, json={"error": True, "reason": "bad hours"}))
    with pytest.raises(ProviderError, match="bad hours"):
        OpenMeteoClient(httpx.Client()).fetch_hourly_forecasts([(40, -100)], T0, T0)
