/** Calls to the trip-planning API. */
import { getJson, postJson } from '../lib/api'
import type { Heatmap, Place, Plan, PlanRequest } from '../types'

export const searchPlaces = (query: string, signal?: AbortSignal) =>
  getJson<Place[]>(`/api/places/?q=${encodeURIComponent(query)}`, signal)

export const planTrip = (request: PlanRequest) => postJson<Plan>('/api/plan/', request)

/**
 * Hourly risk grid for the plan's corridor. Sends the route lines back so the server stays stateless,
 * plus the checkpoints, so the heatmap also samples exactly where the trucks drive.
 */
export const fetchRiskHeatmap = (plan: Plan) =>
  postJson<Heatmap>('/api/heatmap/', {
    routes: plan.routes.map((route) => route.geometry),
    checkpoints: plan.routes.flatMap((route) => route.checkpoints.map((cp) => cp.position)),
    departure: plan.departure,
    load_lb: plan.load_lb,
  })
