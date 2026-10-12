"""Domain results → JSON-ready dicts. Coordinates are [lon, lat] (GeoJSON order)."""

from datetime import datetime

from planner.domain.geometry import Coord
from planner.domain.models import RiskLevel
from planner.service import Checkpoint, Heatmap, PlannedRoute, TripPlan


def risk_level_name(level: RiskLevel | None) -> str | None:
    return None if level is None else level.name.lower()


def _to_lon_lat(c: Coord) -> list[float]:
    return [round(c[1], 5), round(c[0], 5)]


def _to_iso_time(t: datetime) -> str:
    return t.isoformat(timespec="seconds")


def _round_or_none(v: float | None, digits: int) -> float | None:
    return None if v is None else round(v, digits)


def _checkpoint_json(c: Checkpoint) -> dict:
    return {
        "mile": round(c.mile, 1),
        "position": _to_lon_lat(c.coord),
        "eta": _to_iso_time(c.eta),
        "covered_mi": round(c.covered_mi, 2),
        "line_range": list(c.line_range),  # slice of the route's geometry this checkpoint covers
        "weather": {
            "wind_mph": _round_or_none(c.weather.wind_mph, 1),
            "gust_mph": _round_or_none(c.weather.gust_mph, 1),
            "rain_in_hr": _round_or_none(c.weather.rain_in_hr, 3),
            "snow_in_hr": _round_or_none(c.weather.snow_in_hr, 2),
        },
        "risk": {
            "overall": risk_level_name(c.risk.overall),
            "wind": risk_level_name(c.risk.wind),
            "rain": risk_level_name(c.risk.rain),
            "snow": risk_level_name(c.risk.snow),
            "reasons": list(c.risk.reasons),
        },
    }


def _route_json(r: PlannedRoute, rank: int, plan: TripPlan) -> dict:
    s = r.summary
    return {
        "id": r.id,
        "name": r.name,
        "generated": r.generated,
        "rank": rank,
        "recommended": r.id == plan.recommended_id,
        "explanation": plan.explanations.get(r.id, ""),
        "geometry": [_to_lon_lat(c) for c in r.line],
        "distance_mi": round(r.distance_mi, 1),
        "drive_s": round(r.drive_s),
        "trip_s": round(r.trip_s),
        "arrival": _to_iso_time(r.arrival),
        "summary": {
            "miles_by_level": {risk_level_name(lv): round(mi, 1) for lv, mi in s.miles_by_level.items()},
            "unknown_mi": round(s.unknown_mi, 1),
            "avg_risk": _round_or_none(s.avg_risk, 2),
            "max_level": risk_level_name(s.max_level),
            "disqualified": s.disqualified,
        },
        "checkpoints": [_checkpoint_json(c) for c in r.checkpoints],
        "stops": [
            {"kind": st.kind, "position": _to_lon_lat(st.coord), "mile": round(st.mile, 1), "start": _to_iso_time(st.start), "end": _to_iso_time(st.end)}
            for st in r.stops
        ],
        "track": [[round(t), *_to_lon_lat(c)] for t, c in r.track],
    }


def plan_to_json(plan: TripPlan) -> dict:
    return {
        "departure": _to_iso_time(plan.request.departure),
        "load_lb": plan.request.load_lb,
        "interval_mi": plan.request.interval_mi,
        "apply_hos": plan.request.apply_hos,
        "recommended_id": plan.recommended_id,
        "warnings": plan.warnings,
        "routes": [_route_json(r, i + 1, plan) for i, r in enumerate(plan.routes)],
    }


def heatmap_to_json(h: Heatmap) -> dict:
    return {
        "start": _to_iso_time(h.start),
        "hours": h.hours,
        "spacing_km": round(h.spacing_km, 2),
        "cell_deg": [round(h.cell_deg[0], 6), round(h.cell_deg[1], 6)],  # [dlat, dlon]
        "levels": [risk_level_name(lv) for lv in RiskLevel],  # index → name for `risk` values
        "points": [_to_lon_lat(p) for p in h.points],
        "risk": h.risk,
    }
