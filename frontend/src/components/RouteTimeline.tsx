import { useEffect, useRef } from 'react'
import { formatDateTime, formatDuration } from '../utils/format.utils'
import { riskColor, riskLabel } from '../utils/risk.utils'
import { buildTimelineRows, type TimelineRow } from '../utils/timeline.utils'
import type { SelectedPoint, Checkpoint, Route } from '../types'

export function RiskBadge({ level }: { level: Checkpoint['risk']['overall'] }) {
  return (
    <span className="chip" style={{ background: riskColor(level) }}>
      {riskLabel(level)}
    </span>
  )
}

const formatValue = (v: number | null, digits: number, unit: string) => (v === null ? '—' : `${v.toFixed(digits)} ${unit}`)

export function WeatherSummary({ weather }: { weather: Checkpoint['weather'] }) {
  return (
    <span className="weather">
      Wind {formatValue(weather.wind_mph, 0, 'mph')}
      {weather.gust_mph !== null && ` (gust ${weather.gust_mph.toFixed(0)})`} · Rain {formatValue(weather.rain_in_hr, 2, 'in/hr')} ·
      Snow {formatValue(weather.snow_in_hr, 1, 'in/hr')}
    </span>
  )
}

interface Props {
  route: Route
  selectedPoint: SelectedPoint | null
  onSelectPoint: (point: SelectedPoint) => void
}

export function RouteTimeline({ route, selectedPoint, onSelectPoint }: Props) {
  const listRef = useRef<HTMLOListElement>(null)
  const rows = buildTimelineRows(route)

  const isSelected = (row: TimelineRow) =>
    selectedPoint?.routeId === route.id && selectedPoint.kind === row.kind && selectedPoint.index === row.index

  // Bring the row into view when the point was picked on the map.
  useEffect(() => {
    if (selectedPoint?.from === 'map') listRef.current?.querySelector('.active')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [selectedPoint])

  const selectRow = (row: TimelineRow) => onSelectPoint({ routeId: route.id, kind: row.kind, index: row.index, from: 'list' })

  return (
    <section className="route-detail">
      <h3>
        {route.name} timeline <span className="muted">· {route.checkpoints.length} checkpoints</span>
      </h3>
      <ol className="timeline" ref={listRef}>
        {rows.map((row) =>
          row.kind === 'checkpoint' ? (
            <li key={`c${row.index}`} className={isSelected(row) ? 'active' : ''}>
              <button type="button" onClick={() => selectRow(row)} aria-current={isSelected(row)}>
                <span className="mile">mi {row.cp.mile.toFixed(0)}</span>
                <span className="eta">{formatDateTime(row.cp.eta)}</span>
                <RiskBadge level={row.cp.risk.overall} />
                <WeatherSummary weather={row.cp.weather} />
                {row.cp.risk.reasons.length > 0 && <span className="reasons">{row.cp.risk.reasons.join(' · ')}</span>}
              </button>
            </li>
          ) : (
            <li key={`s${row.index}`} className={`stop-row${isSelected(row) ? ' active' : ''}`}>
              <button type="button" onClick={() => selectRow(row)} aria-current={isSelected(row)}>
                <span className="mile">mi {row.stop.mile.toFixed(0)}</span>
                <span className="eta">{formatDateTime(row.stop.start)}</span>
                <span className="stop-label">
                  {row.stop.kind === 'rest' ? '10-hour rest' : '30-min break'} · resume {formatDateTime(row.stop.end)}
                </span>
              </button>
            </li>
          ),
        )}
      </ol>
      <p className="muted small">
        Driving {formatDuration(route.drive_s)} · total trip {formatDuration(route.trip_s)}
      </p>
    </section>
  )
}
