"""How risky is each route, and which one do we recommend?

Ranking compares routes criterion by criterion, moving to the next only on a tie:
  0. Any No Travel checkpoint disqualifies the route
  1. Fewest Severe miles
  2. Fewest High miles
  3. Lowest average risk
  4. Shortest travel time
Values are rounded before comparing (0.1 mi, 0.01 risk, 1 min) so float noise never decides a winner.

Example: A has 25 Severe mi (fastest), B has 50 High mi, C has 25 High mi (slowest).
B and C beat A on Severe miles, C beats B on High miles → order C, B, A.
"""

from collections.abc import Callable
from dataclasses import dataclass

from .models import RiskLevel


@dataclass(frozen=True)
class RouteSummary:
    """A route's risk totals: miles at each level, average risk, worst level, travel time."""

    route_id: str
    distance_mi: float
    trip_s: float  # departure to arrival, including stops
    miles_by_level: dict[RiskLevel, float]
    unknown_mi: float  # miles whose forecast was unavailable
    avg_risk: float | None  # distance-weighted 0–4 score over known miles
    max_level: RiskLevel | None

    @property
    def disqualified(self) -> bool:
        return self.miles_by_level[RiskLevel.NO_TRAVEL] > 0

    @property
    def severe_mi(self) -> float:
        return self.miles_by_level[RiskLevel.SEVERE]

    @property
    def high_mi(self) -> float:
        return self.miles_by_level[RiskLevel.HIGH]

    @property
    def no_travel_mi(self) -> float:
        return self.miles_by_level[RiskLevel.NO_TRAVEL]


def summarize_route_risk(
    route_id: str, distance_mi: float, trip_s: float, levels: list[RiskLevel | None], miles: list[float]
) -> RouteSummary:
    """Add up each checkpoint's covered miles by its risk level.

    Example: levels [Low, Moderate, Severe, Moderate, Low] covering [12.5, 25, 25, 25, 12.5] mi
    → Severe 25 mi, Moderate 50 mi, Low 25 mi, and average risk (0·25 + 1·50 + 3·25) / 100 = 1.25.
    Unknown checkpoints are counted separately and left out of the average.
    """
    by_level = {level: 0.0 for level in RiskLevel}
    unknown = 0.0
    for level, mi in zip(levels, miles):
        if level is None:
            unknown += mi
        else:
            by_level[level] += mi
    known = sum(by_level.values())
    avg = sum(level * mi for level, mi in by_level.items()) / known if known else None
    max_level = max((lv for lv in levels if lv is not None), default=None)
    return RouteSummary(route_id, distance_mi, trip_s, by_level, unknown, avg, max_level)


@dataclass(frozen=True)
class Criterion:
    """One ranking criterion: how to compare routes on it, and the words used in explanations."""

    better: str  # phrase when this route wins on the criterion
    worse: str
    key: Callable[[RouteSummary], float]
    fmt: Callable[[float], str]


def _miles(v: float) -> str:
    return f"{v:g} mi"


def _hours(minutes: float) -> str:
    return f"{minutes // 60:.0f}h {minutes % 60:02.0f}m"


CRITERIA = [
    Criterion(
        "fewer No Travel miles", "more No Travel miles",
        lambda s: round(s.no_travel_mi, 1) if s.disqualified else 0, _miles,
    ),
    Criterion("fewer Severe miles", "more Severe miles", lambda s: round(s.severe_mi, 1), _miles),
    Criterion("fewer High miles", "more High miles", lambda s: round(s.high_mi, 1), _miles),
    Criterion(
        "lower average risk", "higher average risk",
        lambda s: round(s.avg_risk, 2) if s.avg_risk is not None else float("inf"), lambda v: f"{v:.2f}",
    ),
    Criterion("shorter travel time", "longer travel time", lambda s: round(s.trip_s / 60), _hours),
]


def _ranking_sort_key(s: RouteSummary) -> tuple:
    """Python compares tuples item by item, which gives "next criterion only on a tie" for free."""
    return (s.disqualified, *(c.key(s) for c in CRITERIA))


@dataclass(frozen=True)
class Ranking:
    order: list[str]  # route ids, best first
    recommended_id: str | None  # None when every route is disqualified
    explanations: dict[str, str]


def _first_criterion_that_differs(a: RouteSummary, b: RouteSummary) -> tuple[Criterion, float, float] | None:
    """The criterion that decided between two routes, with both values, for the explanation."""
    for c in CRITERIA:
        va, vb = c.key(a), c.key(b)
        if va != vb:
            return c, va, vb
    return None


def _explain_recommendation(best: RouteSummary, runner_up: RouteSummary | None, name: dict[str, str]) -> str:
    if best.disqualified:
        return "Every route crosses No Travel conditions, this one is the least bad."
    if runner_up is None:
        return "Only route available."
    diff = _first_criterion_that_differs(best, runner_up)
    if diff is None:
        return f"Recommended: identical on every criterion to {name[runner_up.route_id]}."
    c, vb, vr = diff
    return f"Recommended: {c.better} than {name[runner_up.route_id]} ({c.fmt(vb)} vs {c.fmt(vr)})."


def _explain_why_ranked_lower(s: RouteSummary, best: RouteSummary, name: dict[str, str]) -> str:
    if s.disqualified and not best.disqualified:
        return f"Not recommended: {_miles(round(s.no_travel_mi, 1))} in No Travel conditions."
    diff = _first_criterion_that_differs(s, best)
    if diff is None:
        return f"Tied with {name[best.route_id]} on every criterion."
    c, vs, vb = diff
    return f"Ranked below {name[best.route_id]}: {c.worse} ({c.fmt(vs)} vs {c.fmt(vb)})."


def rank_routes(summaries: list[RouteSummary], names: dict[str, str]) -> Ranking:
    """Order routes best first, pick the recommendation and explain every position.

    Example explanations: "Recommended: fewer High miles than Route B (25 mi vs 50 mi)."
    and "Ranked below Route C: more Severe miles (25 mi vs 0 mi)."
    `names` maps route id → display name. No route is recommended if every one is disqualified.
    """
    ordered = sorted(summaries, key=_ranking_sort_key)  # stable: ties keep provider order
    best = ordered[0]
    explanations = {best.route_id: _explain_recommendation(best, ordered[1] if len(ordered) > 1 else None, names)}
    for s in ordered[1:]:
        explanations[s.route_id] = _explain_why_ranked_lower(s, best, names)
    recommended = None if best.disqualified else best.route_id
    return Ranking([s.route_id for s in ordered], recommended, explanations)
