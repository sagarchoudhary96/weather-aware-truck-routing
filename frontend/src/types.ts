// Mirrors the backend API. Positions are [lon, lat].

export type RiskLevelName = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel'
export type LonLat = [number, number]

export interface Place {
  label: string
  lat: number
  lon: number
}

export interface PlanRequest {
  origin: Place
  destination: Place
  departure: string
  load_lb: number
  interval_mi: 10 | 25 | 50
  apply_hos: boolean
}

export interface Checkpoint {
  mile: number
  position: LonLat
  eta: string
  covered_mi: number
  line_range: [number, number] // first and last index of this checkpoint's stretch in Route.geometry
  weather: {
    wind_mph: number | null
    gust_mph: number | null
    rain_in_hr: number | null
    snow_in_hr: number | null
  }
  risk: {
    overall: RiskLevelName | null
    wind: RiskLevelName | null
    rain: RiskLevelName | null
    snow: RiskLevelName | null
    reasons: string[]
  }
}

export interface Stop {
  kind: 'break' | 'rest'
  position: LonLat
  mile: number
  start: string
  end: string
}

export interface Route {
  id: string
  name: string
  generated: boolean
  rank: number
  recommended: boolean
  explanation: string
  geometry: LonLat[]
  distance_mi: number
  drive_s: number
  trip_s: number
  arrival: string
  summary: {
    miles_by_level: Record<RiskLevelName, number>
    unknown_mi: number
    avg_risk: number | null
    max_level: RiskLevelName | null
    disqualified: boolean
  }
  checkpoints: Checkpoint[]
  stops: Stop[]
  track: [number, number, number][] // [seconds since departure, lon, lat]
}

export interface Plan {
  departure: string
  load_lb: number
  interval_mi: number
  apply_hos: boolean
  recommended_id: string | null
  warnings: string[]
  routes: Route[]
}

/** A checkpoint or driver stop picked in the list or on the map. */
export interface SelectedPoint {
  routeId: string
  kind: 'checkpoint' | 'stop'
  index: number
  from: 'list' | 'map' // the map only flies to points picked in the list
}

export interface Heatmap {
  start: string // time of the first value in each `risk` row
  step_minutes: number
  hours: number // length of the slider
  spacing_km: number
  cell_deg: [number, number] // [dlat, dlon]
  levels: RiskLevelName[]
  points: LonLat[] // cell centres
  risk: (number | null)[][] // [cell][step] risk level index
}
