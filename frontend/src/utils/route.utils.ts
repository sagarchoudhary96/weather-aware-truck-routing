import type { LonLat, Route, SelectedPoint } from '../types'

/** South-west and north-east corners around all the lines, for fitting the map to the routes. */
export function boundingBox(lines: LonLat[][]): [LonLat, LonLat] {
  let [minX, minY, maxX, maxY] = [Infinity, Infinity, -Infinity, -Infinity]
  for (const line of lines)
    for (const [x, y] of line) {
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x)
      maxY = Math.max(maxY, y)
    }
  return [
    [minX, minY],
    [maxX, maxY],
  ]
}

/**
 * Truck position at `elapsedS` seconds after departure. The backend records the track every
 * 10 minutes, between two samples the position is blended so playback glides smoothly.
 */
export function truckPositionAt(track: Route['track'], elapsedS: number): LonLat {
  if (elapsedS <= track[0][0]) return [track[0][1], track[0][2]]
  for (let i = 1; i < track.length; i++) {
    const [t1, x1, y1] = track[i]
    if (elapsedS <= t1) {
      const [t0, x0, y0] = track[i - 1]
      const fraction = t1 > t0 ? (elapsedS - t0) / (t1 - t0) : 0
      return [x0 + (x1 - x0) * fraction, y0 + (y1 - y0) * fraction]
    }
  }
  const last = track[track.length - 1]
  return [last[1], last[2]]
}

/** Whether the truck is driving, on a driver stop, or has arrived at `elapsedS` after departure. */
export function truckStatusAt(route: Route, departure: string, elapsedS: number): 'driving' | 'stopped' | 'arrived' {
  if (elapsedS >= route.trip_s) return 'arrived'
  const t = Date.parse(departure) + elapsedS * 1000
  return route.stops.some((s) => t >= Date.parse(s.start) && t < Date.parse(s.end)) ? 'stopped' : 'driving'
}

/** The route and checkpoint or stop behind a selection, and where it is on the map. */
export function findSelectedPoint(routes: Route[], selectedPoint: SelectedPoint | null) {
  const route = selectedPoint ? routes.find((r) => r.id === selectedPoint.routeId) : undefined
  const checkpoint = selectedPoint?.kind === 'checkpoint' ? route?.checkpoints[selectedPoint.index] : undefined
  const stop = selectedPoint?.kind === 'stop' ? route?.stops[selectedPoint.index] : undefined
  return { route, checkpoint, stop, position: (checkpoint ?? stop)?.position }
}
