import type { FeatureCollection } from 'geojson'
import type { ExpressionSpecification } from 'maplibre-gl'
import { useMemo } from 'react'
import { Layer, Source } from 'react-map-gl/maplibre'
import { RISK_COLOR } from '../constants/risk.constants'
import type { Heatmap, RiskLevelName } from '../types'

/**
 * MapLibre's heatmap layer sums nearby weights, which suits density but not per-cell values.
 * So we stack one heatmap layer per risk level: layer L counts only cells at level ≥ L, in L's
 * colour. Neighbours can make a patch larger or more solid but never a higher colour, so the top
 * colour visible anywhere is the highest level actually forecast there.
 */

const LEVELS: { level: number; key: RiskLevelName }[] = [
  { level: 1, key: 'moderate' },
  { level: 2, key: 'high' },
  { level: 3, key: 'severe' },
  { level: 4, key: 'no_travel' },
]
const EARTH_CIRCUMFERENCE_M = 40_075_016.686
const RADIUS_PER_CELL = 1.5 // kernel radius relative to grid spacing, so neighbouring cells merge
// MapLibre's kernel peaks at 0.399 × weight × intensity, this makes a lone cell's peak ≈ 1.
const INTENSITY = 2.5
const FULL_COLOR_DENSITY = 0.35 // density at which a level reaches full colour
const ALPHA = 0.8
const BELOW_LAYER = 'route-casing' // heatmap loads after the routes, keep it underneath them

function hexToRgba(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`
}

function heatmapPointFeatures(h: Heatmap): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: h.points.map((p, i) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: p },
      properties: Object.fromEntries(h.risk[i].map((v, hr) => [`h${hr}`, v])),
    })),
  }
}

/** 0–1 weight for level L at a fractional hour: the blended risk value's share above L − 1. */
function levelWeightExpression(level: number, hour: number, maxHour: number): ExpressionSpecification {
  const h0 = Math.floor(hour)
  const h1 = Math.min(h0 + 1, maxHour)
  const f = hour - h0
  const value: ExpressionSpecification = [
    '+',
    ['*', ['coalesce', ['get', `h${h0}`], 0], 1 - f],
    ['*', ['coalesce', ['get', `h${h1}`], 0], f],
  ]
  return ['min', 1, ['max', 0, ['-', value, level - 1]]]
}

function kernelRadiusExpression(h: Heatmap): ExpressionSpecification {
  const lat = h.points.reduce((s, p) => s + p[1], 0) / Math.max(h.points.length, 1)
  const metersPerPxAtZ0 = (EARTH_CIRCUMFERENCE_M * Math.cos((lat * Math.PI) / 180)) / 512
  const r0 = (RADIUS_PER_CELL * h.spacing_km * 1000) / metersPerPxAtZ0
  return ['interpolate', ['exponential', 2], ['zoom'], 0, r0, 16, r0 * 2 ** 16]
}

interface Props {
  heatmap: Heatmap
  hour: number
  visible: boolean
}

export function RiskHeatmap({ heatmap, hour, visible }: Props) {
  const features = useMemo(() => heatmapPointFeatures(heatmap), [heatmap])
  const radius = useMemo(() => kernelRadiusExpression(heatmap), [heatmap])

  return (
    <Source id="level-heat" type="geojson" data={features}>
      {LEVELS.map(({ level, key }) => (
        <Layer
          key={key}
          id={`level-heat-${key}`}
          type="heatmap"
          beforeId={BELOW_LAYER}
          layout={{ visibility: visible ? 'visible' : 'none' }}
          paint={{
            'heatmap-weight': levelWeightExpression(level, hour, heatmap.hours),
            'heatmap-intensity': INTENSITY,
            'heatmap-radius': radius,
            'heatmap-color': [
              'interpolate',
              ['linear'],
              ['heatmap-density'],
              0,
              hexToRgba(RISK_COLOR[key], 0),
              FULL_COLOR_DENSITY,
              hexToRgba(RISK_COLOR[key], ALPHA),
            ],
          }}
        />
      ))}
    </Source>
  )
}
