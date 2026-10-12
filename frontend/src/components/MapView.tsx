import { useMemo, useRef, useState } from 'react'
import Map, {
  Layer,
  type MapLayerMouseEvent,
  type MapRef,
  Marker,
  NavigationControl,
  Popup,
  ScaleControl,
  Source,
} from 'react-map-gl/maplibre'
import { useMapCamera } from '../hooks/useMapCamera'
import { useRouteMapData } from '../hooks/useRouteMapData'
import { formatDateTime, formatDuration, formatMiles } from '../utils/format.utils'
import { findSelectedPoint, truckPositionAt, truckStatusAt } from '../utils/route.utils'
import type { SelectedPoint, Heatmap, LonLat, Plan, Route } from '../types'
import { RiskBadge, WeatherSummary } from './RouteTimeline'
import { RiskHeatmap } from './RiskHeatmap'

const STYLE_URL = 'https://tiles.openfreemap.org/styles/positron'

interface Props {
  plan: Plan | null
  heatmap: Heatmap | null
  showHeatmap: boolean
  hour: number
  selectedRouteId: string | null
  onSelectRoute: (id: string) => void
  selectedPoint: SelectedPoint | null
  onSelectPoint: (point: SelectedPoint | null) => void
  onLoad: () => void
}

/** Route labels sit on the middle checkpoint, roughly halfway along the route. */
function routeLabelPosition(route: Route): LonLat {
  return route.checkpoints[Math.floor(route.checkpoints.length / 2)].position
}

export function MapView({ plan, heatmap, showHeatmap, hour, selectedRouteId, onSelectRoute, selectedPoint, onSelectPoint, onLoad }: Props) {
  const mapRef = useRef<MapRef>(null)
  const [cursor, setCursor] = useState('')

  const routes = useMemo(() => plan?.routes ?? [], [plan])
  const selected = routes.find((r) => r.id === selectedRouteId) ?? null
  const { routeLines, selectedRouteRiskSegments, checkpointFeatures, tripEnds } = useRouteMapData(routes, selectedRouteId)

  const selection = findSelectedPoint(routes, selectedPoint)
  useMapCamera(mapRef, routes, selectedPoint, selection.position)

  const handleMapClick = (e: MapLayerMouseEvent) => {
    const f = e.features?.[0]
    if (!f) return onSelectPoint(null)
    if (f.layer.id === 'checkpoints') {
      onSelectPoint({ routeId: f.properties.routeId, kind: 'checkpoint', index: f.properties.index, from: 'map' })
    } else onSelectRoute(f.properties.id)
  }

  const elapsedS = hour * 3600

  return (
    <Map
      ref={mapRef}
      initialViewState={{ longitude: -98.5, latitude: 39.5, zoom: 3.6 }}
      mapStyle={STYLE_URL}
      interactiveLayerIds={['route-hit', 'checkpoints']}
      onClick={handleMapClick}
      onLoad={onLoad}
      onMouseEnter={() => setCursor('pointer')}
      onMouseLeave={() => setCursor('')}
      cursor={cursor}
      style={{ position: 'absolute', inset: 0 }}
    >
      <NavigationControl position="top-right" showCompass={false} />
      <ScaleControl position="bottom-right" unit="imperial" />

      <Source id="routes" type="geojson" data={routeLines}>
        <Layer
          id="route-casing"
          type="line"
          layout={{ 'line-join': 'round', 'line-cap': 'round', 'line-sort-key': ['case', ['get', 'selected'], 1, 0] }}
          paint={{
            'line-color': ['case', ['get', 'selected'], '#14213d', '#ffffff'],
            'line-width': ['case', ['get', 'selected'], 9, 6],
          }}
        />
        <Layer
          id="route-line"
          type="line"
          layout={{ 'line-join': 'round', 'line-cap': 'round', 'line-sort-key': ['case', ['get', 'selected'], 1, 0] }}
          paint={{
            'line-color': ['case', ['get', 'selected'], '#14213d', '#7c8799'],
            'line-width': ['case', ['get', 'selected'], 5, 3.5],
          }}
        />
        <Layer id="route-hit" type="line" paint={{ 'line-width': 16, 'line-opacity': 0 }} />
      </Source>

      {heatmap && <RiskHeatmap heatmap={heatmap} hour={hour} visible={showHeatmap} />}

      <Source id="segments" type="geojson" data={selectedRouteRiskSegments}>
        <Layer
          id="route-risk"
          type="line"
          layout={{ 'line-join': 'round', 'line-cap': 'butt' }}
          paint={{ 'line-color': ['get', 'color'], 'line-width': 5 }}
        />
      </Source>

      <Source id="checkpoints" type="geojson" data={checkpointFeatures}>
        <Layer
          id="checkpoints"
          type="circle"
          layout={{ 'circle-sort-key': ['case', ['get', 'selected'], 1, 0] }}
          paint={{
            'circle-color': ['get', 'color'],
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, ['case', ['get', 'selected'], 4, 2.5], 10, ['case', ['get', 'selected'], 8, 5]],
            'circle-stroke-color': ['case', ['get', 'selected'], '#14213d', '#ffffff'],
            'circle-stroke-width': ['case', ['get', 'selected'], 1.5, 1],
            'circle-opacity': ['case', ['get', 'selected'], 1, 0.75],
          }}
        />
      </Source>

      {selection.position && (
        <Marker longitude={selection.position[0]} latitude={selection.position[1]} anchor="center">
          <div className="focus-ring" aria-hidden />
        </Marker>
      )}

      {tripEnds &&
        (['start', 'end'] as const).map((end) => (
          <Marker key={end} longitude={tripEnds[end][0]} latitude={tripEnds[end][1]} anchor="bottom" offset={[0, -6]}>
            <div className={`trip-end-pin ${end}`}>{end === 'start' ? 'Start' : 'End'}</div>
          </Marker>
        ))}

      {selected?.stops.map((s, index) => (
        <Marker key={s.start} longitude={s.position[0]} latitude={s.position[1]} anchor="bottom">
          <button
            type="button"
            className={`stop-marker ${s.kind}`}
            onClick={(e) => {
              e.stopPropagation()
              onSelectPoint({ routeId: selected.id, kind: 'stop', index, from: 'map' })
            }}
          >
            {s.kind === 'rest' ? 'Rest 10h' : 'Break'}
          </button>
        </Marker>
      ))}

      {routes.map((r) => {
        const [lon, lat] = routeLabelPosition(r)
        return (
          <Marker key={`label-${r.id}`} longitude={lon} latitude={lat} anchor="left" offset={[10, 0]}>
            <button
              type="button"
              className={`route-label${r.id === selectedRouteId ? ' selected' : ''}${r.recommended ? ' recommended' : ''}`}
              onClick={(e) => {
                e.stopPropagation()
                onSelectRoute(r.id)
              }}
            >
              <b>{r.id}</b> {formatDuration(r.trip_s)} · {formatMiles(r.distance_mi)}
              {r.recommended && ' ★'}
              {r.summary.disqualified && ' ⛔'}
            </button>
          </Marker>
        )
      })}

      {routes.map((r) => {
        const [lon, lat] = truckPositionAt(r.track, elapsedS)
        const state = truckStatusAt(r, plan!.departure, elapsedS)
        return (
          <Marker key={`truck-${r.id}`} longitude={lon} latitude={lat} anchor="center">
            <div className={`truck ${state}${r.id === selectedRouteId ? ' selected' : ''}`} title={`${r.name}: ${state}`}>
              {r.id}
            </div>
          </Marker>
        )
      })}

      {selection.route && selection.checkpoint && (
        <Popup
          longitude={selection.checkpoint.position[0]}
          latitude={selection.checkpoint.position[1]}
          onClose={() => onSelectPoint(null)}
          closeOnClick={false}
          offset={14}
          maxWidth="300px"
        >
          <div className="cp-popup">
            <div className="cp-popup-head">
              <strong>
                {selection.route.name} · mile {selection.checkpoint.mile.toFixed(0)}
              </strong>
              <RiskBadge level={selection.checkpoint.risk.overall} />
            </div>
            <div>ETA {formatDateTime(selection.checkpoint.eta)}</div>
            <WeatherSummary weather={selection.checkpoint.weather} />
            {selection.checkpoint.risk.reasons.map((reason) => (
              <div key={reason} className="reason">
                {reason}
              </div>
            ))}
            <div className="muted small">Represents {formatMiles(selection.checkpoint.covered_mi)} of road</div>
          </div>
        </Popup>
      )}

      {selection.route && selection.stop && (
        <Popup
          longitude={selection.stop.position[0]}
          latitude={selection.stop.position[1]}
          onClose={() => onSelectPoint(null)}
          closeOnClick={false}
          offset={14}
          maxWidth="260px"
        >
          <div className="cp-popup">
            <strong>
              {selection.route.name} · {selection.stop.kind === 'rest' ? '10-hour rest' : '30-min break'}
            </strong>
            <div>Mile {selection.stop.mile.toFixed(0)}</div>
            <div>
              {formatDateTime(selection.stop.start)} → {formatDateTime(selection.stop.end)}
            </div>
            <div className="muted small">
              {selection.stop.kind === 'rest' ? 'Required after 11 h of driving' : 'Required after 8 h of driving'}
            </div>
          </div>
        </Popup>
      )}
    </Map>
  )
}
