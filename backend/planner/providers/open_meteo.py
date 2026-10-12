"""Open-Meteo hourly forecasts (free, no API key), fetched for many locations per request."""

import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from django.core.cache import cache

from planner.domain.geometry import Coord
from planner.domain.models import Weather

from .errors import ProviderError

log = logging.getLogger(__name__)

URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"
CHUNK_SIZE = 100  # locations per request
COORD_DECIMALS = 2  # ~1 km, nearby points share one lookup
FORECAST_HORIZON = timedelta(days=15)
CACHE_TTL_S = 30 * 60
HOUR_S = 3600


@dataclass(frozen=True)
class HourlyForecast:
    start: int  # unix seconds of the first hour, values are hourly from there
    wind: list[float | None]
    gust: list[float | None]
    rain: list[float | None]  # rain + showers, in/hr
    snow: list[float | None]  # snowfall depth, in/hr

    def _value_for_hour(self, series: list[float | None], ts: int) -> float | None:
        i = (ts - self.start) // HOUR_S
        return series[i] if 0 <= i < len(series) else None

    def weather_at_time(self, t: datetime) -> Weather:
        """Wind is instantaneous, so use the nearest hour. Rain and snow are totals over the
        preceding hour, so use the hour the truck is driving in: the one starting at or before t.
        Example: 14:20 and exactly 14:00 both use the 14:00–15:00 total (labelled 15:00).
        This also keeps the heatmap at slider time 14:00 in step with a truck arriving then."""
        ts = t.timestamp()
        nearest = round(ts / HOUR_S) * HOUR_S
        bucket_end = (math.floor(ts / HOUR_S) + 1) * HOUR_S
        return Weather(
            wind_mph=self._value_for_hour(self.wind, nearest),
            gust_mph=self._value_for_hour(self.gust, nearest),
            rain_in_hr=self._value_for_hour(self.rain, bucket_end),
            snow_in_hr=self._value_for_hour(self.snow, bucket_end),
        )


def _start_of_hour(t: datetime) -> datetime:
    return t.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _add_unless_missing(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a + b


def _parse_location_forecast(item: dict) -> HourlyForecast:
    h = item["hourly"]
    return HourlyForecast(
        start=h["time"][0],
        wind=h["wind_speed_10m"],
        gust=h["wind_gusts_10m"],
        rain=[_add_unless_missing(r, s) for r, s in zip(h["rain"], h["showers"])],
        snow=h["snowfall"],
    )


class OpenMeteoClient:
    def __init__(self, http: httpx.Client | None = None):
        self.http = http or httpx.Client(timeout=20)

    def fetch_hourly_forecasts(self, points: list[Coord], start: datetime, end: datetime) -> list[HourlyForecast]:
        """Hourly forecasts covering [start, end] for each point, in input order."""
        first = _start_of_hour(start)
        last = min(_start_of_hour(end) + timedelta(hours=1), _start_of_hour(datetime.now(UTC) + FORECAST_HORIZON))
        window = (first.strftime("%Y-%m-%dT%H:%M"), max(first, last).strftime("%Y-%m-%dT%H:%M"))

        keys = [(round(lat, COORD_DECIMALS), round(lon, COORD_DECIMALS)) for lat, lon in points]
        cache_key = {k: f"om:{k[0]}:{k[1]}:{window[0]}:{window[1]}" for k in set(keys)}
        found = {k: v for k, v in ((k, cache.get(ck)) for k, ck in cache_key.items()) if v is not None}

        missing = [k for k in cache_key if k not in found]
        chunks = [missing[i : i + CHUNK_SIZE] for i in range(0, len(missing), CHUNK_SIZE)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for chunk, results in zip(chunks, pool.map(lambda c: self._request_batch(c, window), chunks)):
                for k, forecast in zip(chunk, results):
                    found[k] = forecast
                    cache.set(cache_key[k], forecast, CACHE_TTL_S)

        return [found[k] for k in keys]

    def _request_batch(self, chunk: list[tuple[float, float]], window: tuple[str, str]) -> list[HourlyForecast]:
        params = {
            "latitude": ",".join(str(lat) for lat, _ in chunk),
            "longitude": ",".join(str(lon) for _, lon in chunk),
            "hourly": HOURLY_VARS,
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "GMT",
            "timeformat": "unixtime",
            "start_hour": window[0],
            "end_hour": window[1],
        }
        for attempt in range(2):
            try:
                response = self.http.get(URL, params=params)
            except httpx.HTTPError as exc:
                log.warning("Open-Meteo request failed: %s", exc)
                if attempt:
                    raise ProviderError("Weather service is unreachable.") from exc
                continue
            if response.status_code == 429 or response.status_code >= 500:
                log.warning("Open-Meteo returned %s", response.status_code)
                if not attempt:
                    time.sleep(1.5)
                    continue
                raise ProviderError("Weather service is busy, please retry shortly.")
            if response.status_code != 200:
                reason = response.json().get("reason", response.text[:200])
                raise ProviderError(f"Weather service rejected the request: {reason}")
            data = response.json()
            return [_parse_location_forecast(item) for item in (data if isinstance(data, list) else [data])]
        raise ProviderError("Weather service is unreachable.")
