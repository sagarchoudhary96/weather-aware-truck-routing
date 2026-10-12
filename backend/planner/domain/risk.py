"""What is the weather risk at one place and time? Uses the assignment's risk table and load rules.

    Wind (mph)    < 25 Low | 25 Moderate | 35 High | 45 Severe | 55+ No Travel
    Rain (in/hr)  < 0.10   | 0.10        | 0.25    | 0.50      | > 1.00
    Snow (in/hr)  < 0.5    | 0.5         | 1.0     | 2.0       | > 3.0

A value exactly on a band's lower bound belongs to that band (35 mph is High). The top
rain and snow bands are strictly greater than (rain 1.00 in/hr is Severe, not No Travel).
"""

from dataclasses import dataclass

from .models import RiskLevel, Weather

L, M, H, S, NT = RiskLevel

# Lower bounds (inclusive) for Moderate, High and Severe.
RAIN_BOUNDS_IN_HR = (0.10, 0.25, 0.50)
SNOW_BOUNDS_IN_HR = (0.5, 1.0, 2.0)
RAIN_NO_TRAVEL_ABOVE = 1.00
SNOW_NO_TRAVEL_ABOVE = 3.0

# Lower bounds (inclusive) for Moderate, High, Severe and No Travel.
WIND_BOUNDS_MPH = (25, 35, 45, 55)

HEAVY_LOAD_LB = 30_000  # 45–54 mph above this → No Travel
VERY_HEAVY_LOAD_LB = 40_000  # 35–44 mph above this → Severe


@dataclass(frozen=True)
class RiskAssessment:
    """Risk per condition, the overall (worst) level, and why. Shown in checkpoint popups."""

    wind: RiskLevel | None
    rain: RiskLevel | None
    snow: RiskLevel | None
    overall: RiskLevel | None  # None when any input is missing
    reasons: tuple[str, ...]  # human-readable drivers of any non-Low level


def _as_reported(value: float) -> str:
    """The forecast value as Open-Meteo reports it (wind to 0.1 mph, rain and snow to 0.001 in),
    so it never looks like it sits in another band. Example: 34.7 → "34.7", not "35" (High)."""
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _level_for_value(value: float, bounds: tuple[float, ...]) -> RiskLevel:
    """Highest band whose lower bound the value reaches. Example: 37 mph with (25, 35, 45, 55) → High."""
    level = L
    for i, bound in enumerate(bounds, start=1):
        if value >= bound:
            level = RiskLevel(i)
    return level


def classify_rain(in_hr: float) -> RiskLevel:
    """Example: 0.30 in/hr → High, 1.00 → Severe, 1.01 → No Travel."""
    return NT if in_hr > RAIN_NO_TRAVEL_ABOVE else _level_for_value(in_hr, RAIN_BOUNDS_IN_HR)


def classify_snow(in_hr: float) -> RiskLevel:
    """Example: 0.7 in/hr → Moderate, 3.0 → Severe, 3.1 → No Travel."""
    return NT if in_hr > SNOW_NO_TRAVEL_ABOVE else _level_for_value(in_hr, SNOW_BOUNDS_IN_HR)


def classify_wind(mph: float, load_lb: float) -> tuple[RiskLevel, str | None]:
    """Wind level from the table, then the load rules, which can only make it worse.

    - 45–54 mph with a load over 30,000 lb → No Travel (instead of Severe)
    - 35–44 mph with a load over 40,000 lb → Severe (instead of High)
    Examples: 50 mph + 35,000 lb → No Travel, 40 mph + exactly 40,000 lb → stays High.
    Returns (level, the load rule that applied, if any).
    """
    level = _level_for_value(mph, WIND_BOUNDS_MPH)
    if level == S and load_lb > HEAVY_LOAD_LB:
        return NT, f"load over {HEAVY_LOAD_LB:,} lb"
    if level == H and load_lb > VERY_HEAVY_LOAD_LB:
        return S, f"load over {VERY_HEAVY_LOAD_LB:,} lb"
    return level, None


def assess_weather_risk(weather: Weather, load_lb: float) -> RiskAssessment:
    """Overall risk is the worst of wind, rain and snow. Gusts are ignored.

    Example: wind 30 mph (Moderate), rain 0.3 in/hr (High), no snow → High,
    reasons ("Wind 30 mph → Moderate", "Rain 0.3 in/hr → High").
    Any missing value makes the overall level None (Unknown), never Low.
    """
    wind = rain = snow = None
    reasons: list[str] = []

    if weather.wind_mph is not None:
        wind, load_rule = classify_wind(weather.wind_mph, load_lb)
        if wind > L:
            rule = f" + {load_rule}" if load_rule else ""
            reasons.append(f"Wind {_as_reported(weather.wind_mph)} mph{rule} → {wind.label}")
    if weather.rain_in_hr is not None:
        rain = classify_rain(weather.rain_in_hr)
        if rain > L:
            reasons.append(f"Rain {_as_reported(weather.rain_in_hr)} in/hr → {rain.label}")
    if weather.snow_in_hr is not None:
        snow = classify_snow(weather.snow_in_hr)
        if snow > L:
            reasons.append(f"Snow {_as_reported(weather.snow_in_hr)} in/hr → {snow.label}")

    levels = (wind, rain, snow)
    overall = None if None in levels else max(levels)
    return RiskAssessment(wind, rain, snow, overall, tuple(reasons))
