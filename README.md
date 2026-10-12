# Weather-Aware Truck Routing

Compares three truck routes using the forecast weather the truck will meet **when it reaches each point**, and recommends the safest one.

- **Live app:** _TBD_
- **Walkthrough (Loom):** _TBD_

## How it works

```
TomTom truck routes ──► driver breaks ──► checkpoints + ETAs ──► Open-Meteo hourly forecast
                                                                         │
            ranking ◄── miles per risk level ◄── risk per checkpoint ◄───┘
```

The map shows the routes, risk-coloured checkpoints, driver stops and a corridor risk heatmap with a 0–48 h slider.

## Rules and assumptions

| | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | < 25 | 25 – < 35 | 35 – < 45 | 45 – < 55 | ≥ 55 |
| Rain (in/hr) | < 0.10 | 0.10 – < 0.25 | 0.25 – < 0.50 | 0.50 – 1.00 | > 1.00 |
| Snow (in/hr) | < 0.5 | 0.5 – < 1.0 | 1.0 – < 2.0 | 2.0 – 3.0 | > 3.0 |

- **Load rules** raise the wind level only. 45–54 mph with a load over 30,000 lb is No Travel, 35–44 mph with a load over 40,000 lb is Severe.
- **Checkpoint risk** is the worst of wind (sustained, not gusts), rain (including showers) and snow. A missing value counts as Unknown, never Low.
- **Forecast hour:** wind uses the hour nearest the ETA. Rain and snow use the hourly total that contains the ETA, so an ETA of 14:20 uses the 14:00–15:00 total.
- **Miles per level:** each checkpoint covers half the gap to each neighbour. **Average risk** scores Low 0 to No Travel 4, weighted by miles.
- **Ranking:** any No Travel disqualifies a route. Routes are then compared on fewest Severe miles, then fewest High miles, then lowest average risk, then shortest travel time.
- **Driver breaks (US Hours of Service):** a 30-minute break after 8 h of driving and a 10-hour rest after 11 h. Breaks can be switched off in the form.
- **Truck:** the user enters cargo weight. Routing adds 35,000 lb for the tractor-trailer and caps speed at 65 mph.
- **Inputs:** departure up to 7 days ahead, load 0–80,000 lb, US locations.

These rules are covered by tests in `backend/tests/`.

## Repository

| Folder | What | Docs |
|---|---|---|
| `backend/` | Django API: routing, forecasts, risk, ranking | [backend/README.md](backend/README.md) |
| `frontend/` | React + MapLibre web app | [frontend/README.md](frontend/README.md) |

## Quick start

You need a free [TomTom API key](https://developer.tomtom.com). Open-Meteo needs no key.

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && cp .env.example .env    # set TOMTOM_API_KEY
python manage.py runserver                                     # http://localhost:8000
```

In a second terminal:

```bash
cd frontend && npm install && npm run dev                      # http://localhost:5173
```

Both parts deploy to Vercel on the free Hobby plan, as two projects from this repo. Each folder's README has the settings.

## Known limits

- Free API quotas apply. Forecasts are cached for 30 minutes and routes for 10, within each running server instance.
- Driver stops are placed where the driving clock runs out, not at real truck stops.
