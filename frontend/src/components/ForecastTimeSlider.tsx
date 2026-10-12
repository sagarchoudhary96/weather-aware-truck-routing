import { formatDateTime } from '../utils/format.utils'

const SLIDER_STEP_HOURS = 10 / 60 // matches the backend's 10-minute truck track

interface Props {
  hour: number
  maxHour: number
  departure: string
  onChange: (hour: number) => void
  playing: boolean
  onTogglePlay: () => void
  onStopPlay: () => void
  onDraggingChange: (dragging: boolean) => void
  showHeatmap: boolean
  onToggleHeatmap: (show: boolean) => void
  status: string | null
}

export function ForecastTimeSlider({
  hour,
  maxHour,
  departure,
  onChange,
  playing,
  onTogglePlay,
  onStopPlay,
  onDraggingChange,
  showHeatmap,
  onToggleHeatmap,
  status,
}: Props) {
  const at = new Date(Date.parse(departure) + hour * 3600_000)
  const whole = Math.floor(hour)
  const minutes = Math.round((hour - whole) * 60)

  return (
    <div className="time-slider">
      <button type="button" className="play" aria-label={playing ? 'Pause' : 'Play'} onClick={onTogglePlay}>
        {playing ? '❚❚' : '▶'}
      </button>
      <div className="slider-body">
        <div className="slider-label">
          <strong>
            T+{whole}h{minutes ? ` ${String(minutes).padStart(2, '0')}m` : ''}
          </strong>
          <span>{formatDateTime(at)}</span>
          {status && <span className="muted">{status}</span>}
        </div>
        <input
          type="range"
          min={0}
          max={maxHour}
          step={SLIDER_STEP_HOURS}
          value={hour}
          aria-label="Hours after departure"
          onChange={(e) => {
            onStopPlay()
            onChange(Number(e.target.value))
          }}
          onPointerDown={() => onDraggingChange(true)}
          onPointerUp={() => onDraggingChange(false)}
          onPointerCancel={() => onDraggingChange(false)}
        />
        <div className="ticks" aria-hidden>
          {[0, 12, 24, 36, 48].map((h) => (
            <span key={h}>{h}h</span>
          ))}
        </div>
      </div>
      <label className="toggle">
        <input type="checkbox" checked={showHeatmap} onChange={(e) => onToggleHeatmap(e.target.checked)} />
        Heatmap
      </label>
    </div>
  )
}
