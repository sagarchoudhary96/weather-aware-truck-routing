import { formatDateTime, formatDuration, formatMiles } from '../utils/format.utils'
import { RISK_COLOR, RISK_LABEL, RISK_LEVELS } from '../constants/risk.constants'
import { riskLabel } from '../utils/risk.utils'
import type { Route } from '../types'

function RiskMilesBar({ route }: { route: Route }) {
  const total = route.distance_mi || 1
  const breakdown = RISK_LEVELS.filter((level) => route.summary.miles_by_level[level] > 0)
    .map((level) => `${RISK_LABEL[level]} ${formatMiles(route.summary.miles_by_level[level])}`)
    .join(' · ')
  return (
    <div className="risk-bar" aria-hidden title={breakdown}>
      {RISK_LEVELS.map((level) => {
        const mi = route.summary.miles_by_level[level]
        return mi > 0 ? (
          <span key={level} style={{ width: `${(mi / total) * 100}%`, background: RISK_COLOR[level] }} />
        ) : null
      })}
    </div>
  )
}

function RouteCard({ route, selected, onSelectRoute }: { route: Route; selected: boolean; onSelectRoute: () => void }) {
  const { summary: s } = route
  return (
    <button
      type="button"
      className={`route-card${selected ? ' selected' : ''}${s.disqualified ? ' disqualified' : ''}`}
      onClick={onSelectRoute}
      aria-pressed={selected}
    >
      <div className="route-card-head">
        <span className="rank">#{route.rank}</span>
        <strong>{route.name}</strong>
        {route.generated && <span className="tag">detour</span>}
        {route.recommended && <span className="tag recommended">Recommended</span>}
        {s.disqualified && <span className="tag danger">No Travel</span>}
      </div>

      <div className="route-stats">
        <span>{formatMiles(route.distance_mi)}</span>
        <span title="Including driver breaks">{formatDuration(route.trip_s)}</span>
        <span>Arrive {formatDateTime(route.arrival)}</span>
      </div>

      <RiskMilesBar route={route} />

      <dl className="risk-miles">
        {(['no_travel', 'severe', 'high'] as const).map((level) => (
          <div key={level}>
            <dt>{RISK_LABEL[level]}</dt>
            <dd>{formatMiles(s.miles_by_level[level])}</dd>
          </div>
        ))}
        <div>
          <dt>Avg risk</dt>
          <dd>{s.avg_risk?.toFixed(2) ?? '—'}</dd>
        </div>
        <div>
          <dt>Worst</dt>
          <dd>{riskLabel(s.max_level)}</dd>
        </div>
      </dl>

      <p className="explanation">{route.explanation}</p>
    </button>
  )
}

/** Grey placeholder cards shown while the first plan is loading. */
export function RouteListSkeleton() {
  return (
    <div className="route-list" aria-hidden>
      {[0, 1, 2].map((i) => (
        <div key={i} className="route-card skeleton-card">
          <span className="skeleton-line short" />
          <span className="skeleton-line" />
          <span className="skeleton-line bar" />
          <span className="skeleton-line" />
        </div>
      ))}
    </div>
  )
}

interface Props {
  routes: Route[]
  selectedRouteId: string | null
  onSelectRoute: (id: string) => void
}

export function RouteList({ routes, selectedRouteId, onSelectRoute }: Props) {
  return (
    <div className="route-list">
      {routes.map((r) => (
        <RouteCard key={r.id} route={r} selected={r.id === selectedRouteId} onSelectRoute={() => onSelectRoute(r.id)} />
      ))}
    </div>
  )
}
