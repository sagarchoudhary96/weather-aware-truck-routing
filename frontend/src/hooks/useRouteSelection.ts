import { useCallback, useState } from 'react'
import type { Plan, SelectedPoint } from '../types'

interface Selection {
  planVersion: number
  routeId: string | null
  point: SelectedPoint | null
}

/**
 * The selected route and checkpoint/stop. The selection is tied to the plan it was made for,
 * so a new plan starts on its recommended route with nothing picked.
 */
export function useRouteSelection(plan: Plan | null, planVersion: number) {
  const [stored, setStored] = useState<Selection>({ planVersion, routeId: null, point: null })

  const forCurrentPlan = useCallback(
    (s: Selection): Selection =>
      s.planVersion === planVersion ? s : { planVersion, routeId: plan?.recommended_id ?? plan?.routes[0]?.id ?? null, point: null },
    [plan, planVersion],
  )
  const selection = forCurrentPlan(stored)

  const selectRoute = useCallback(
    (routeId: string) =>
      setStored((s) => {
        const { point } = forCurrentPlan(s)
        return { planVersion, routeId, point: point?.routeId === routeId ? point : null } // close another route's popup
      }),
    [forCurrentPlan, planVersion],
  )

  const selectPoint = useCallback(
    (point: SelectedPoint | null) =>
      setStored((s) => ({ planVersion, routeId: point ? point.routeId : forCurrentPlan(s).routeId, point })),
    [forCurrentPlan, planVersion],
  )

  return {
    selectedRouteId: selection.routeId,
    selectedRoute: plan?.routes.find((r) => r.id === selection.routeId) ?? null,
    selectRoute,
    selectedPoint: selection.point,
    selectPoint,
  }
}
