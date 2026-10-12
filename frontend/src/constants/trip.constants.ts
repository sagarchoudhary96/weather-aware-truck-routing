import type { PlanRequest } from '../types'

export const CHECKPOINT_INTERVALS_MI = [10, 25, 50] as const
export const MAX_LOAD_LB = 80_000 // matches the backend's limit

export const EXAMPLE_TRIP: Pick<PlanRequest, 'origin' | 'destination'> = {
  origin: { label: 'Chicago, IL, United States', lat: 41.8781, lon: -87.6298 },
  destination: { label: 'Denver, CO, United States', lat: 39.7392, lon: -104.9903 },
}
