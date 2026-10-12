# Frontend

The web app lets a driver plan a trip and compare the ranked routes. It shows each route's checkpoints, driver stops and the weather risk heatmap on a map.

## Run

Requires Node 20+ and the backend running (see `../backend`).

```bash
npm install
npm run dev        # http://localhost:5173
```

`VITE_API_URL` sets the backend URL (default `http://localhost:8000`). It's read only in `src/config/appConfig.ts`.

| Script | Purpose |
|---|---|
| `npm run dev` | Dev server |
| `npm run build` | Type-check and production build to `dist/` |
| `npm test` | Unit tests (Vitest), in `__tests__/` folders next to the code |
| `npm run lint` | Lint (oxlint) |

## Structure

| Folder | Role |
|---|---|
| `src/` | App entry (`main.tsx`), page layout (`App.tsx`), API types (`types.ts`), styles |
| `src/components/` | UI: trip form and autocomplete, route cards and timeline, map with heatmap, legend and forecast slider |
| `src/hooks/` | Component logic: planning and route selection, form fields, place search, heatmap query, slider hour and playback, map camera and layer data |
| `src/config/` | `appConfig.ts`: the only place that reads environment variables |
| `src/services/` | API calls (`planner.service.ts`: place search, trip plan, risk heatmap) |
| `src/constants/` | Shared fixed values: risk levels, colours and labels, checkpoint intervals, load limit, example trip |
| `src/utils/` | Pure helpers: truck position and status, selected point lookup, timeline rows, map bounds, formatting, risk colour/label lookups |
| `src/lib/` | Wrappers and setup for external tools: generic HTTP client, MapLibre worker |

## Map behaviour

- The selected route is coloured by checkpoint risk: click any route to select it.
- Checkpoints and stops are linked between the timeline and the map.
- The slider moves the trucks and the heatmap through 0–48 h. The heatmap changes every half hour, using the same forecast hours as the route checkpoints, so it matches them when the slider is still. While playing or dragging it fades between half hours to move smoothly.
- The heatmap uses one MapLibre heatmap layer per risk level, so overlapping cells never show a higher risk than they have.

## Deploy (Vercel, free tier)

- **Root directory:** `frontend`
- **Framework preset:** Vite
- **Build:** `npm run build`
- **Output:** `dist`
- **Env:** `VITE_API_URL=<backend URL>`
