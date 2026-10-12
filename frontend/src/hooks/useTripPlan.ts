import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { planTrip as requestPlan } from '../services/planner.service'
import type { Plan } from '../types'

/** Requests trip plans and keeps the latest one. `planVersion` goes up with every new plan. */
export function useTripPlan() {
  // Kept outside the mutation so the previous plan stays on screen while the next one loads.
  const [latest, setLatest] = useState<{ plan: Plan | null; version: number }>({ plan: null, version: 0 })

  const request = useMutation({
    mutationFn: requestPlan,
    onSuccess: (plan) => setLatest((prev) => ({ plan, version: prev.version + 1 })),
  })

  return {
    plan: latest.plan,
    planVersion: latest.version,
    planTrip: request.mutate,
    isPlanning: request.isPending,
    error: request.error,
  }
}
