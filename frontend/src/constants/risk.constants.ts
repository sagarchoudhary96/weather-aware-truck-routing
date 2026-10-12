import type { RiskLevelName } from '../types'

export const RISK_LEVELS: RiskLevelName[] = ['low', 'moderate', 'high', 'severe', 'no_travel']

export const RISK_COLOR: Record<RiskLevelName, string> = {
  low: '#2f9e5b',
  moderate: '#e3b505',
  high: '#f07c1b',
  severe: '#d62f2f',
  no_travel: '#6d1b7b',
}

export const UNKNOWN_COLOR = '#9aa3af'

export const RISK_LABEL: Record<RiskLevelName, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  severe: 'Severe',
  no_travel: 'No Travel',
}
