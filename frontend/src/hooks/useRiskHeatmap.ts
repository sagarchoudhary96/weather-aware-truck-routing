import { useQuery } from '@tanstack/react-query'
import { fetchRiskHeatmap } from '../services/planner.service'
import type { Plan } from '../types'

/** The corridor risk heatmap, fetched once per plan, and a status line for the slider. */
export function useRiskHeatmap(plan: Plan | null, planVersion: number) {
  const query = useQuery({
    queryKey: ['heatmap', planVersion],
    queryFn: () => fetchRiskHeatmap(plan!),
    enabled: plan !== null,
    staleTime: Infinity,
  })

  const status = query.isFetching ? 'Loading forecast heatmap…' : query.error ? query.error.message : null
  return { heatmap: query.data ?? null, status }
}
