import { useState } from 'react'
import { EXAMPLE_TRIP, MAX_LOAD_LB } from '../constants/trip.constants'
import { toDateTimeInputValue } from '../utils/format.utils'
import type { Place, PlanRequest } from '../types'

function nextFullHourLocal(): string {
  const d = new Date()
  d.setHours(d.getHours() + 1, 0, 0, 0)
  return toDateTimeInputValue(d)
}

/** The trip form's fields, whether they're valid, and the plan request they make on submit. */
export function useTripForm(onSubmit: (req: PlanRequest) => void) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(nextFullHourLocal)
  const [load, setLoad] = useState('35000')
  const [intervalMi, setIntervalMi] = useState<PlanRequest['interval_mi']>(25)
  const [applyDriverBreaks, setApplyDriverBreaks] = useState(true)
  const [minDeparture] = useState(() => toDateTimeInputValue(new Date()))

  const loadLb = Number(load)
  const isValid =
    origin !== null && destination !== null && departure !== '' && load !== '' && loadLb >= 0 && loadLb <= MAX_LOAD_LB

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid) return
    onSubmit({
      origin,
      destination,
      departure: new Date(departure).toISOString(),
      load_lb: loadLb,
      interval_mi: intervalMi,
      apply_hos: applyDriverBreaks,
    })
  }

  const fillExampleTrip = () => {
    setOrigin(EXAMPLE_TRIP.origin)
    setDestination(EXAMPLE_TRIP.destination)
  }

  return {
    origin,
    setOrigin,
    destination,
    setDestination,
    departure,
    setDeparture,
    minDeparture,
    load,
    setLoad,
    intervalMi,
    setIntervalMi,
    applyDriverBreaks,
    setApplyDriverBreaks,
    isValid,
    handleSubmit,
    fillExampleTrip,
  }
}
