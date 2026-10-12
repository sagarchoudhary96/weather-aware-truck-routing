import { MapPanel } from './components/MapPanel'
import { RouteTimeline } from './components/RouteTimeline'
import { RouteList, RouteListSkeleton } from './components/RouteList'
import { TripForm } from './components/TripForm'
import { useRouteSelection } from './hooks/useRouteSelection'
import { useTripPlan } from './hooks/useTripPlan'
import { formatPounds } from './utils/format.utils'

export default function App() {
  const { plan, planVersion, planTrip, isPlanning, error } = useTripPlan()
  const { selectedRouteId, selectedRoute, selectRoute, selectedPoint, selectPoint } = useRouteSelection(plan, planVersion)

  return (
    <div className="app">
      <aside className="panel">
        <header>
          <h1>Weather-Aware Truck Routing</h1>
          <p className="muted">Compares three routes by forecast weather at each checkpoint's arrival time.</p>
        </header>

        <TripForm loading={isPlanning} onSubmit={planTrip} />

        {error && <div className="error">{error.message}</div>}

        {isPlanning && !plan && <RouteListSkeleton />}

        {plan && (
          // While re-planning, the previous results stay visible but dimmed.
          <div className={`plan-results${isPlanning ? ' is-stale' : ''}`}>
            <div className="plan-meta muted small">
              {formatPounds(plan.load_lb)} · checkpoints every {plan.interval_mi} mi ·{' '}
              {plan.apply_hos ? 'with driver breaks' : 'no driver breaks'}
            </div>
            {plan.warnings.map((w) => (
              <div key={w} className="warning">
                {w}
              </div>
            ))}
            <RouteList routes={plan.routes} selectedRouteId={selectedRouteId} onSelectRoute={selectRoute} />
            {selectedRoute && <RouteTimeline route={selectedRoute} selectedPoint={selectedPoint} onSelectPoint={selectPoint} />}
          </div>
        )}
      </aside>

      <main className="map-area">
        <MapPanel
          plan={plan}
          planVersion={planVersion}
          isPlanning={isPlanning}
          selectedRouteId={selectedRouteId}
          onSelectRoute={selectRoute}
          selectedPoint={selectedPoint}
          onSelectPoint={selectPoint}
        />
      </main>
    </div>
  )
}
