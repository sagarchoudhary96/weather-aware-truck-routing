"""TomTom Routing (truck mode) and Search (address autocomplete)."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

import httpx
from django.core.cache import cache

from planner.domain.geometry import Coord, RouteWithTimings, route_with_timings_from_segments

from .errors import NoRouteError, ProviderError

log = logging.getLogger(__name__)

ROUTE_URL = "https://api.tomtom.com/routing/1/calculateRoute/{locations}/json"
SEARCH_URL = "https://api.tomtom.com/search/2/search/{query}.json"
KG_PER_LB = 0.45359237
# TomTom restricts roads by gross vehicle weight; the user enters cargo weight.
TRUCK_TARE_LB = 35_000
# Typical fleet speed governor; without it TomTom assumes posted limits (~73 mph averages).
TRUCK_MAX_SPEED_KMH = 105  # 65 mph
ROUTE_CACHE_S = 10 * 60  # re-planning with a different checkpoint interval reuses routes


@dataclass(frozen=True)
class TruckRoute:
    route_timings: RouteWithTimings
    notices: list[str]


@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lon: float


def gross_vehicle_weight_kg(load_lb: float) -> int:
    return round((TRUCK_TARE_LB + load_lb) * KG_PER_LB)


def parse_route_with_timings(route: dict) -> TruckRoute:
    """Build route timings from the route's points and its guidance instructions, which carry the
    cumulative travel time at a point index. Time between instructions is spread by distance."""
    points: list[Coord] = [(p["latitude"], p["longitude"]) for leg in route["legs"] for p in leg["points"]]
    last_index = len(points) - 1

    # Driving seconds from the start, known at the points where instructions occur.
    seconds_at_point: dict[int, float] = {0: 0.0}
    for instruction in route.get("guidance", {}).get("instructions", []):
        index = min(instruction["pointIndex"], last_index)
        seconds_at_point.setdefault(index, instruction["travelTimeInSeconds"])
    seconds_at_point.setdefault(last_index, route["summary"]["travelTimeInSeconds"])

    timed_indices = sorted(seconds_at_point)
    seconds = [seconds_at_point[i] for i in timed_indices]
    for i in range(1, len(seconds)):  # guard against out-of-order timestamps
        seconds[i] = max(seconds[i], seconds[i - 1])
    segment_durations = [end - start for start, end in zip(seconds, seconds[1:])]
    return TruckRoute(route_with_timings_from_segments(points, timed_indices[:-1], segment_durations), notices=[])


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    err = body.get("detailedError") or body.get("error") or {}
    return err.get("message") or err.get("description") or str(body)[:200]


class TomTomClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None):
        if not api_key:
            raise ProviderError("TOMTOM_API_KEY is not configured.")
        self.api_key = api_key
        self.http = http or httpx.Client(timeout=30)

    def _get(self, url: str, params: dict) -> dict:
        try:
            response = self.http.get(url, params={**params, "key": self.api_key})
        except httpx.HTTPError as exc:
            log.warning("TomTom request failed: %s", exc)
            raise ProviderError("Routing service is unreachable.") from exc
        if response.status_code in (401, 403):
            raise ProviderError("Routing service rejected the API key.")
        if response.status_code == 429:
            raise ProviderError("Routing service rate limit reached; please retry shortly.")
        if response.status_code != 200:
            message = _error_message(response)
            log.warning("TomTom returned %s: %s", response.status_code, message)
            if "NO_ROUTE" in message.upper().replace(" ", "_") or "no route" in message.lower():
                raise NoRouteError("No truck route found between these points.")
            raise ProviderError(f"Routing request failed: {message}")
        return response.json()

    def fetch_truck_routes(
        self,
        origin: Coord,
        destination: Coord,
        departure: datetime,
        load_lb: float,
        alternatives: int = 0,
        via: Coord | None = None,
    ) -> list[TruckRoute]:
        points = [origin, *([via] if via else []), destination]
        params = {
            "travelMode": "truck",
            "vehicleCommercial": "true",
            "vehicleWeight": gross_vehicle_weight_kg(load_lb),
            "vehicleMaxSpeed": TRUCK_MAX_SPEED_KMH,
            "routeType": "fastest",
            "traffic": "true",
            "instructionsType": "coded",
            "maxAlternatives": alternatives,
            "departAt": departure.isoformat(timespec="seconds") if departure > datetime.now(UTC) else "now",
        }
        locations = ":".join(f"{lat},{lon}" for lat, lon in points)
        cache_key = f"route:{locations}:{params['vehicleWeight']}:{alternatives}:{params['departAt'][:16]}"
        if (cached := cache.get(cache_key)) is not None:
            return cached
        data = self._get(ROUTE_URL.format(locations=locations), params)
        routes = data.get("routes") or []
        if not routes:
            raise NoRouteError("No truck route found between these points.")
        parsed = [parse_route_with_timings(r) for r in routes]
        cache.set(cache_key, parsed, ROUTE_CACHE_S)
        return parsed

    def search_places(self, query: str, limit: int = 6) -> list[Place]:
        data = self._get(
            SEARCH_URL.format(query=quote(query, safe='')),
            {"typeahead": "true", "limit": limit, "countrySet": "US", "idxSet": "Geo,PAD,Addr,Str,POI"},
        )
        places = []
        for item in data.get("results", []):
            address = item.get("address", {}).get("freeformAddress", "")
            name = item.get("poi", {}).get("name")
            label = f"{name}, {address}" if name else address
            places.append(Place(label, item["position"]["lat"], item["position"]["lon"]))
        return places
