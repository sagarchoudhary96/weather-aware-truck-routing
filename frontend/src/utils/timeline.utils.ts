import type { Checkpoint, Route, Stop } from '../types'

export type TimelineRow =
  | { kind: 'checkpoint'; at: string; index: number; cp: Checkpoint }
  | { kind: 'stop'; at: string; index: number; stop: Stop }

/** A route's checkpoints and driver stops in one list, in time order. */
export function buildTimelineRows(route: Route): TimelineRow[] {
  return [
    ...route.checkpoints.map((cp, index) => ({ kind: 'checkpoint' as const, at: cp.eta, index, cp })),
    ...route.stops.map((stop, index) => ({ kind: 'stop' as const, at: stop.start, index, stop })),
  ].sort((a, b) => a.at.localeCompare(b.at))
}
