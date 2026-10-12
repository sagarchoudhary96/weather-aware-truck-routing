import type { FeatureCollection } from 'geojson'
import { useMemo } from 'react'
import { riskColor } from '../utils/risk.utils'
import type { Route } from '../types'

/**
 * GeoJSON for the map layers: every route line, the selected route cut into risk-coloured pieces,
 * the checkpoint dots, and the trip's start and end points.
 */
export function useRouteMapData(routes: Route[], selectedRouteId: string | null) {
  return useMemo(() => {
    const selected = routes.find((r) => r.id === selectedRouteId) ?? null

    const routeLines: FeatureCollection = {
      type: 'FeatureCollection',
      features: routes.map((r) => ({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: r.geometry },
        properties: { id: r.id, selected: r.id === selectedRouteId },
      })),
    }

    const selectedRouteRiskSegments: FeatureCollection = {
      type: 'FeatureCollection',
      features: selected
        ? selected.checkpoints.map((cp) => ({
            // The backend splits the line at checkpoint boundaries, each checkpoint covers one slice.
            type: 'Feature',
            geometry: { type: 'LineString', coordinates: selected.geometry.slice(cp.line_range[0], cp.line_range[1] + 1) },
            properties: { id: selected.id, color: riskColor(cp.risk.overall) },
          }))
        : [],
    }

    const checkpointFeatures: FeatureCollection = {
      type: 'FeatureCollection',
      features: routes.flatMap((r) =>
        r.checkpoints.map((cp, index) => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: cp.position },
          properties: { routeId: r.id, index, color: riskColor(cp.risk.overall), selected: r.id === selectedRouteId },
        })),
      ),
    }

    // Every route shares the same road-snapped start and end points.
    const tripEnds = routes.length ? { start: routes[0].geometry[0], end: routes[0].geometry.at(-1)! } : null

    return { routeLines, selectedRouteRiskSegments, checkpointFeatures, tripEnds }
  }, [routes, selectedRouteId])
}
