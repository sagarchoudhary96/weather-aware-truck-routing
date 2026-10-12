import { CHECKPOINT_INTERVALS_MI, MAX_LOAD_LB } from '../constants/trip.constants'
import { useTripForm } from '../hooks/useTripForm'
import type { PlanRequest } from '../types'
import { PlaceAutocomplete } from './PlaceAutocomplete'

interface Props {
  loading: boolean
  onSubmit: (req: PlanRequest) => void
}

export function TripForm({ loading, onSubmit }: Props) {
  const form = useTripForm(onSubmit)

  return (
    <form className="trip-form" onSubmit={form.handleSubmit}>
      <PlaceAutocomplete label="Origin" value={form.origin} onChange={form.setOrigin} />
      <PlaceAutocomplete label="Destination" value={form.destination} onChange={form.setDestination} />

      <div className="row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            value={form.departure}
            min={form.minDeparture}
            onChange={(e) => form.setDeparture(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="load">Load weight (lb)</label>
          <input
            id="load"
            type="number"
            inputMode="numeric"
            min={0}
            max={MAX_LOAD_LB}
            step={500}
            value={form.load}
            onChange={(e) => form.setLoad(e.target.value)}
          />
        </div>
      </div>

      <div className="row">
        <div className="field">
          <span className="label">Weather checkpoints every</span>
          <div className="segmented" role="radiogroup" aria-label="Checkpoint interval">
            {CHECKPOINT_INTERVALS_MI.map((mi) => (
              <button
                type="button"
                key={mi}
                role="radio"
                aria-checked={form.intervalMi === mi}
                className={form.intervalMi === mi ? 'on' : ''}
                onClick={() => form.setIntervalMi(mi)}
              >
                {mi} mi
              </button>
            ))}
          </div>
        </div>
        <label className="toggle" title="30-min break after 8 h driving, 10-h rest after 11 h">
          <input
            type="checkbox"
            checked={form.applyDriverBreaks}
            onChange={(e) => form.setApplyDriverBreaks(e.target.checked)}
          />
          Driver breaks (HOS)
        </label>
      </div>

      <div className="actions">
        <button type="submit" className="primary" disabled={!form.isValid || loading}>
          {loading ? (
            <>
              <span className="spinner" aria-hidden /> Planning…
            </>
          ) : (
            'Find safest route'
          )}
        </button>
        <button type="button" className="link" onClick={form.fillExampleTrip}>
          Use example trip
        </button>
      </div>
    </form>
  )
}
