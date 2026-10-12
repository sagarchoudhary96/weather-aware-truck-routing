import pytest

from planner.domain.models import RiskLevel, Weather
from planner.domain.risk import assess_weather_risk, classify_rain, classify_snow, classify_wind

L, M, H, S, NT = RiskLevel


@pytest.mark.parametrize(
    "mph, expected",
    [(0, L), (24.9, L), (25, M), (34.9, M), (35, H), (44.9, H), (45, S), (54.9, S), (55, NT), (80, NT)],
)
def test_wind_bands_light_load(mph, expected):
    assert classify_wind(mph, load_lb=10_000)[0] == expected


@pytest.mark.parametrize(
    "in_hr, expected",
    [(0, L), (0.09, L), (0.10, M), (0.24, M), (0.25, H), (0.49, H), (0.50, S), (1.00, S), (1.01, NT)],
)
def test_rain_bands(in_hr, expected):
    assert classify_rain(in_hr) == expected


@pytest.mark.parametrize(
    "in_hr, expected",
    [(0, L), (0.49, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H), (2.0, S), (3.0, S), (3.1, NT)],
)
def test_snow_bands(in_hr, expected):
    assert classify_snow(in_hr) == expected


@pytest.mark.parametrize(
    "mph, load_lb, expected",
    [
        (60, 0, NT),  # ≥55 mph is No Travel for any load
        (50, 30_000, S),  # rule needs strictly more than 30,000 lb
        (50, 30_001, NT),
        (45, 35_000, NT),
        (54.9, 35_000, NT),
        (40, 40_000, H),  # rule needs strictly more than 40,000 lb
        (40, 40_001, S),
        (35, 45_000, S),
        (34.9, 80_000, M),  # load rules do not touch winds below 35 mph
        (50, 45_000, NT),  # 45–54 rule takes precedence over the 35–44 one
    ],
)
def test_load_rules(mph, load_lb, expected):
    assert classify_wind(mph, load_lb)[0] == expected


def test_overall_is_worst_condition_with_reasons():
    risk = assess_weather_risk(Weather(wind_mph=30, gust_mph=40, rain_in_hr=0.3, snow_in_hr=0), load_lb=20_000)
    assert (risk.wind, risk.rain, risk.snow, risk.overall) == (M, H, L, H)
    assert risk.reasons == ("Wind 30 mph → Moderate", "Rain 0.3 in/hr → High")


def test_load_rule_is_named_in_reason():
    risk = assess_weather_risk(Weather(wind_mph=47, gust_mph=None, rain_in_hr=0, snow_in_hr=0), load_lb=38_000)
    assert risk.overall == NT
    assert risk.reasons == ("Wind 47 mph + load over 30,000 lb → No Travel",)


def test_gusts_do_not_affect_risk():
    risk = assess_weather_risk(Weather(wind_mph=10, gust_mph=70, rain_in_hr=0, snow_in_hr=0), load_lb=45_000)
    assert risk.overall == L


def test_missing_value_makes_overall_unknown():
    risk = assess_weather_risk(Weather(wind_mph=10, gust_mph=None, rain_in_hr=None, snow_in_hr=0), load_lb=0)
    assert risk.overall is None


def test_reasons_never_round_a_value_into_another_band():
    risk = assess_weather_risk(Weather(wind_mph=34.7, gust_mph=None, rain_in_hr=1.004, snow_in_hr=0.97), load_lb=0)
    assert risk.reasons == ("Wind 34.7 mph → Moderate", "Rain 1.004 in/hr → No Travel", "Snow 0.97 in/hr → Moderate")
