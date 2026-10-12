/** Calls to the trip-planning API. */
import { getJson, postJson } from '../lib/api'
import type { Heatmap, Place, Plan, PlanRequest } from '../types'

export const searchPlaces = (query: string, signal?: AbortSignal) =>
  getJson<Place[]>(`/api/places/?q=${encodeURIComponent(query)}`, signal)

export const planTrip = (request: PlanRequest) => postJson<Plan>('/api/plan/', request)

/** Hourly risk grid for the plan's corridor, sends the route lines back so the server stays stateless. */
export const fetchRiskHeatmap = (plan: Plan) =>
  postJson<Heatmap>('/api/heatmap/', {
    routes: plan.routes.map((route) => route.geometry),
    departure: plan.departure,
    load_lb: plan.load_lb,
  })
