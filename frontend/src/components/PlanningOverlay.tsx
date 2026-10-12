import { useEffect, useState } from 'react'

const SLOW_AFTER_MS = 8000 // a plan usually takes 2–5 s

/** Dims the map while a trip is being planned. */
export function PlanningOverlay() {
  const [slow, setSlow] = useState(false)

  useEffect(() => {
    const id = setTimeout(() => setSlow(true), SLOW_AFTER_MS)
    return () => clearTimeout(id)
  }, [])

  return (
    <div className="planning-overlay" role="status" aria-live="polite">
      <div className="planning-card">
        <span className="spinner large" aria-hidden />
        <div>
          <strong>Planning your trip</strong>
          <p>Getting truck routes and the forecast at each checkpoint…</p>
          {slow && <p className="muted">This is taking longer than usual. The routing or weather service may be slow.</p>}
        </div>
      </div>
    </div>
  )
}
