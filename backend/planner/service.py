"""Trip planning: routes → driver stops → checkpoints → weather at ETA → risk → ranking."""

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta

from .domain.driver_breaks import DriverBreakPlan
from .domain.geometry import (
    METERS_PER_MILE,
    Coord,
    checkpoint_distances_from_start_m,
    road_length_covered_by_each_checkpoint,
    detour_waypoints_either_side,
    share_of_route_overlapping,
    reduce_points_for_drawing,
)
from .domain.heatmap_grid import heatmap_cells_around_routes
from .domain.models import Weather
from .domain.risk import RiskAssessment, assess_weather_risk
from .domain.scoring import RouteSummary, rank_routes, summarize_route_risk
from .providers.errors import ProviderError
from .providers.tomtom import TomTomClient, TruckRoute
from .providers.open_meteo import HourlyForecast, OpenMeteoClient

log = logging.getLogger(__name__)

ROUTE_COUNT = 3
DUPLICATE_OVERLAP = 0.9  # routes sharing ≥90% of their path count as the same route
DISPLAY_TOLERANCE_M = 40
TRACK_STEP_S = 10 * 60
HEATMAP_HOURS = 48


@dataclass(frozen=True)
class TripRequest:
    origin: Coord
    destination: Coord
    departure: datetime
    load_lb: float
    interval_mi: int
    apply_hos: bool = True


@dataclass(frozen=True)
class Checkpoint:
    mile: float
    coord: Coord
    eta: datetime
    covered_mi: float
    weather: Weather
    risk: RiskAssessment


@dataclass(frozen=True)
class PlannedStop:
    kind: str
    coord: Coord
    mile: float
    start: datetime
    end: datetime


@dataclass(frozen=True)
class PlannedRoute:
    id: str
    name: str
    generated: bool  # forced through a detour point because the API returned fewer routes
    line: list[Coord]
    distance_mi: float
    drive_s: float
    trip_s: float
    arrival: datetime
    checkpoints: list[Checkpoint]
    stops: list[PlannedStop]
    track: list[tuple[float, Coord]]  # (seconds since departure, position), first 48 h
    summary: RouteSummary
    notices: list[str]


@dataclass(frozen=True)
class TripPlan:
    request: TripRequest
    routes: list[PlannedRoute]  # best first
    recommended_id: str | None
    explanations: dict[str, str]
    warnings: list[str]


@dataclass(frozen=True)
class RouteOption:
    route: TruckRoute
    line: list[Coord]
    generated: bool


def fetch_three_route_options(routing: TomTomClient, req: TripRequest) -> list[RouteOption]:
    """Up to three distinct routes; tops up with detour routes when the API returns fewer."""
    options: list[RouteOption] = []

    def add_unless_duplicate(route: TruckRoute, generated: bool) -> None:
        line = reduce_points_for_drawing(route.route_timings.coords, DISPLAY_TOLERANCE_M)
        if all(share_of_route_overlapping(line, c.line) < DUPLICATE_OVERLAP for c in options):
            options.append(RouteOption(route, line, generated))

    args = (req.origin, req.destination, req.departure, req.load_lb)
    for route in routing.fetch_truck_routes(*args, alternatives=ROUTE_COUNT - 1):
        add_unless_duplicate(route, generated=False)

    if len(options) < ROUTE_COUNT:

        def via_route(via: Coord) -> TruckRoute | None:
            try:
                return routing.fetch_truck_routes(*args, via=via)[0]
            except ProviderError as exc:
                log.info("Detour via %s failed: %s", via, exc)
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            for route in pool.map(via_route, detour_waypoints_either_side(req.origin, req.destination)):
                if route and len(options) < ROUTE_COUNT:
                    add_unless_duplicate(route, generated=True)

    return options[:ROUTE_COUNT]


def _truck_position_timeline(option: RouteOption, break_plan: DriverBreakPlan, trip_s: float) -> list[tuple[float, Coord]]:
    horizon = min(trip_s, HEATMAP_HOURS * 3600)
    times = [*range(0, int(horizon), TRACK_STEP_S), horizon]
    route_timings = option.route.route_timings
    return [(t, route_timings.position_and_distance_after(break_plan.driving_completed_at(t))[0]) for t in times]


@dataclass(frozen=True)
class ScheduledRoute:
    """A route with its driver breaks and checkpoint ETAs, before the weather is known."""

    option: RouteOption
    break_plan: DriverBreakPlan
    checkpoint_positions_m: list[float]
    checkpoint_coords: list[Coord]
    checkpoint_etas: list[datetime]


def _schedule_checkpoints(option: RouteOption, req: TripRequest) -> ScheduledRoute:
    route_timings = option.route.route_timings
    break_plan = DriverBreakPlan.for_total_driving_time(route_timings.total_drive_s, req.apply_hos)
    positions_m = checkpoint_distances_from_start_m(route_timings.total_m, req.interval_mi * METERS_PER_MILE)
    coords, etas = [], []
    for position_m in positions_m:
        coord, drive_s = route_timings.position_and_drive_time_at(position_m)
        coords.append(coord)
        etas.append(req.departure + timedelta(seconds=break_plan.trip_clock_after_driving(drive_s)))
    return ScheduledRoute(option, break_plan, positions_m, coords, etas)


def _build_planned_route(
    route_id: str, scheduled: ScheduledRoute, forecasts: list[HourlyForecast], req: TripRequest
) -> PlannedRoute:
    """Weather and risk at each checkpoint's ETA, driver stops and the route summary."""
    option, break_plan = scheduled.option, scheduled.break_plan
    route_timings = option.route.route_timings
    covered_mi = [m / METERS_PER_MILE for m in road_length_covered_by_each_checkpoint(scheduled.checkpoint_positions_m)]

    checkpoints = []
    for position_m, coord, eta, covered, forecast in zip(
        scheduled.checkpoint_positions_m, scheduled.checkpoint_coords, scheduled.checkpoint_etas, covered_mi, forecasts
    ):
        weather = forecast.weather_at_time(eta)
        risk = assess_weather_risk(weather, req.load_lb)
        checkpoints.append(Checkpoint(position_m / METERS_PER_MILE, coord, eta, covered, weather, risk))

    stops = []
    for stop in break_plan.stops:
        coord, distance_m = route_timings.position_and_distance_after(stop.at_drive_s)
        start = req.departure + timedelta(seconds=break_plan.trip_clock_when_stop_starts(stop))
        end = start + timedelta(seconds=stop.duration_s)
        stops.append(PlannedStop(stop.kind, coord, distance_m / METERS_PER_MILE, start, end))

    trip_s = break_plan.trip_clock_after_driving(route_timings.total_drive_s)
    distance_mi = route_timings.total_m / METERS_PER_MILE
    return PlannedRoute(
        id=route_id,
        name=f"Route {route_id}",
        generated=option.generated,
        line=option.line,
        distance_mi=distance_mi,
        drive_s=route_timings.total_drive_s,
        trip_s=trip_s,
        arrival=req.departure + timedelta(seconds=trip_s),
        checkpoints=checkpoints,
        stops=stops,
        track=_truck_position_timeline(option, break_plan, trip_s),
        summary=summarize_route_risk(route_id, distance_mi, trip_s, [c.risk.overall for c in checkpoints], covered_mi),
        notices=option.route.notices,
    )


def plan_trip(req: TripRequest, routing: TomTomClient, weather: OpenMeteoClient) -> TripPlan:
    # 1. Up to three distinct truck routes.
    options = fetch_three_route_options(routing, req)

    # 2. Checkpoints and ETAs for every route, so all forecasts come from one batched request.
    scheduled = [_schedule_checkpoints(option, req) for option in options]
    all_coords = [coord for s in scheduled for coord in s.checkpoint_coords]
    latest_eta = max(eta for s in scheduled for eta in s.checkpoint_etas)
    forecasts = weather.fetch_hourly_forecasts(all_coords, req.departure, latest_eta)

    # 3. Each route takes its own slice of the forecasts (same order as its checkpoints), then rank.
    routes: list[PlannedRoute] = []
    first = 0
    for route_id, s in zip("ABC", scheduled):
        count = len(s.checkpoint_coords)
        routes.append(_build_planned_route(route_id, s, forecasts[first : first + count], req))
        first += count

    ranking = rank_routes([r.summary for r in routes], {r.id: r.name for r in routes})
    by_id = {r.id: r for r in routes}
    return TripPlan(
        request=req,
        routes=[by_id[i] for i in ranking.order],
        recommended_id=ranking.recommended_id,
        explanations=ranking.explanations,
        warnings=_plan_warnings(routes, ranking.recommended_id),
    )


def _plan_warnings(routes: list[PlannedRoute], recommended_id: str | None) -> list[str]:
    warnings = []
    if recommended_id is None:
        warnings.append("Every route crosses No Travel conditions at this departure time. Consider departing later.")
    if len(routes) < ROUTE_COUNT:
        warnings.append(f"Only {len(routes)} distinct route(s) found between these points.")
    for r in routes:
        if r.summary.unknown_mi:
            warnings.append(f"{r.name}: no forecast for {r.summary.unknown_mi:.0f} mi; excluded from risk totals.")
    return warnings


@dataclass(frozen=True)
class Heatmap:
    start: datetime
    hours: int
    spacing_km: float
    cell_deg: tuple[float, float]  # (dlat, dlon) of each square cell
    points: list[Coord]  # cell centres
    risk: list[list[int | None]]  # [cell][hour] risk level 0–4


def build_risk_heatmap(lines: list[list[Coord]], departure: datetime, load_lb: float, weather: OpenMeteoClient) -> Heatmap:
    """Load-aware risk for corridor cells at departure + 0…48 hours."""
    grid = heatmap_cells_around_routes(lines)
    times = [departure + timedelta(hours=h) for h in range(HEATMAP_HOURS + 1)]
    forecasts = weather.fetch_hourly_forecasts(grid.points, times[0], times[-1])
    risk = []
    for forecast in forecasts:
        row = []
        for t in times:
            level = assess_weather_risk(forecast.weather_at_time(t), load_lb).overall
            row.append(None if level is None else int(level))
        risk.append(row)
    return Heatmap(departure, HEATMAP_HOURS, grid.spacing_km, (grid.dlat, grid.dlon), grid.points, risk)
