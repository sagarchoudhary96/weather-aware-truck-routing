# Backend

The API fetches truck routes and weather forecasts, scores the risk at each checkpoint and ranks the routes. It needs no database, and repeat API calls are cached in memory.

## Run

Requires Python 3.13 and a free [TomTom API key](https://developer.tomtom.com) (no card needed). Open-Meteo needs no key.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # then set TOMTOM_API_KEY
python manage.py runserver      # http://localhost:8000
```

| Variable | Purpose | Default |
|---|---|---|
| `TOMTOM_API_KEY` | Routing and autocomplete | required |
| `DJANGO_SECRET_KEY` | Django signing key; any random string | dev-only value |
| `DJANGO_DEBUG` | `true` for local development | `false` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `DJANGO_HTTPS_ONLY` | `true` in production: redirect to HTTPS and send HSTS | `false` |
| `CORS_ALLOWED_ORIGINS` | Frontend origins | `http://localhost:5173` |

## Structure

| Path | Role |
|---|---|
| `config/` | Django settings and root URLs |
| `api/views.py` | HTTP endpoints: health, places, plan, heatmap |
| `api/serializers.py` | Request validation (departure window, load, interval, origin ≠ destination) |
| `api/presenters.py` | Domain results → JSON |
| `planner/service.py` | Trip pipeline: routes → driver breaks → checkpoints → forecast → risk → ranking; heatmap builder |
| `planner/domain/risk.py` | Risk bands and load rules (`assess_weather_risk`) |
| `planner/domain/scoring.py` | Miles per level, average risk, ranking and explanations (`rank_routes`) |
| `planner/domain/driver_breaks.py` | Hours-of-service stops and trip clock (`DriverBreakPlan`) |
| `planner/domain/geometry.py` | Positions along a route, checkpoints, miles per checkpoint, simplification, detour points |
| `planner/domain/heatmap_grid.py` | Grid cells around the routes (`heatmap_cells_around_routes`) |
| `planner/providers/tomtom.py` | Truck routing and address search |
| `planner/providers/open_meteo.py` | Hourly forecasts, many locations per request |
| `tests/` | Unit and API tests |

`planner/domain/` is pure Python, with no Django or network code.

**Routing.** TomTom truck mode with gross weight (cargo + 35,000 lb tare), a 65 mph cap, departure-time traffic and up to 2 alternatives. Travel time along the route comes from the cumulative time on each guidance instruction. If fewer than 3 distinct routes come back, the service asks for routes through points offset either side of the midpoint. Routes sharing at least 90% of their path count as duplicates.

**Forecasts.** Open-Meteo `wind_speed_10m`, `wind_gusts_10m`, `rain` + `showers`, and `snowfall`, in mph and inches. Locations are rounded to 0.01°, fetched 100 per request in parallel, and cached for 30 minutes.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health/` | Health check |
| GET | `/api/places/?q=denver` | Address autocomplete (US, min 3 characters) |
| POST | `/api/plan/` | Routes, checkpoints, stops, summaries and ranking |
| POST | `/api/heatmap/` | Hourly risk grid (0–48 h) for the corridor |

`POST /api/plan/`

```json
{
  "origin": { "lat": 39.7392, "lon": -104.9903 },
  "destination": { "lat": 40.7608, "lon": -111.891 },
  "departure": "2026-10-13T14:00:00Z",
  "load_lb": 35000,
  "interval_mi": 25,
  "apply_hos": true
}
```

The response has `routes` (best first), each with `geometry`, `distance_mi`, `trip_s`, `arrival`, `summary` (miles per level, average risk, disqualified), `checkpoints` (ETA, weather, risk and reasons, covered miles), `stops`, `track` (truck position over the first 48 h), `rank`, `recommended` and `explanation`. It also carries plan-level `recommended_id` and `warnings`. Coordinates are `[lon, lat]`.

`POST /api/heatmap/` takes `routes` (the plan's geometries), `departure` and `load_lb`. It returns the cell centres, the cell size and a risk level 0–4 for each cell and hour.

**Validation:**
- Departure from 1 hour ago up to 7 days ahead.
- Load from 0 to 80,000 lb.
- Interval 10, 25 or 50.
- Origin and destination at least 1 km apart.

**Errors:**
- 400 for invalid input.
- 422 when no truck route exists.
- 502 when an upstream API fails.

## Tests

```bash
pytest
```

82 tests:
- risk band boundaries and load rules;
- miles per checkpoint and ranking, including ties, rounding and disqualification;
- driver-break schedules;
- geometry;
- provider parsing and caching (mocked HTTP);
- end-to-end API tests with fake providers.

## Deploy (Render, free tier)

- **Root directory:** `backend`
- **Build:** `pip install -r requirements.txt`
- **Start:** `gunicorn config.wsgi --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`
- **Env:** `TOMTOM_API_KEY`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=.onrender.com`, `DJANGO_HTTPS_ONLY=true`, `CORS_ALLOWED_ORIGINS=<frontend URL>`

Use a single worker so the in-memory cache is shared by all requests. Free instances sleep after 15 minutes idle, so the first request after that takes about a minute.
