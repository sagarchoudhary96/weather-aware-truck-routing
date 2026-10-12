import { useState } from 'react'
import { useForecastHour } from '../hooks/useForecastHour'
import { usePlayback } from '../hooks/usePlayback'
import { useRiskHeatmap } from '../hooks/useRiskHeatmap'
import type { SelectedPoint, Plan } from '../types'
import { RiskLegend } from './RiskLegend'
import { MapView } from './MapView'
import { ForecastTimeSlider } from './ForecastTimeSlider'
import { PlanningOverlay } from './PlanningOverlay'

interface Props {
  plan: Plan | null
  planVersion: number
  isPlanning: boolean
  selectedRouteId: string | null
  onSelectRoute: (id: string) => void
  selectedPoint: SelectedPoint | null
  onSelectPoint: (point: SelectedPoint | null) => void
}

/** Owns the slider hour so scrubbing re-renders only the map, not the side panel. */
export function MapPanel({ plan, planVersion, isPlanning, selectedRouteId, onSelectRoute, selectedPoint, onSelectPoint }: Props) {
  const [hour, setHour] = useForecastHour(planVersion)
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [mapLoaded, setMapLoaded] = useState(false)
  const { heatmap, status } = useRiskHeatmap(plan, planVersion)
  const playback = usePlayback(hour, heatmap?.hours ?? 48, setHour)
  const [dragging, setDragging] = useState(false)

  return (
    <div className="map-panel">
      <MapView
        plan={plan}
        heatmap={heatmap}
        showHeatmap={showHeatmap}
        hour={hour}
        fadeHeatmap={playback.playing || dragging} // smooth while moving, exact when still
        selectedRouteId={selectedRouteId}
        onSelectRoute={onSelectRoute}
        selectedPoint={selectedPoint}
        onSelectPoint={onSelectPoint}
        onLoad={() => setMapLoaded(true)}
      />
      {/* The base map stays blank until its style and first tiles arrive. */}
      {!mapLoaded && (
        <div className="map-loading" role="status">
          <span className="spinner" aria-hidden /> Loading map…
        </div>
      )}
      <RiskLegend />
      {plan && (
        <ForecastTimeSlider
          hour={hour}
          maxHour={heatmap?.hours ?? 48}
          departure={plan.departure}
          onChange={setHour}
          playing={playback.playing}
          onTogglePlay={playback.togglePlay}
          onStopPlay={playback.stop}
          onDraggingChange={setDragging}
          showHeatmap={showHeatmap}
          onToggleHeatmap={setShowHeatmap}
          status={status}
        />
      )}
      {isPlanning && <PlanningOverlay />}
    </div>
  )
}
