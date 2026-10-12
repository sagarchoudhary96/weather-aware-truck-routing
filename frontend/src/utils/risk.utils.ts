import { RISK_COLOR, RISK_LABEL, UNKNOWN_COLOR } from '../constants/risk.constants'
import type { RiskLevelName } from '../types'

/** Colour for a risk level, grey when the forecast was missing (level is null). */
export const riskColor = (level: RiskLevelName | null) => (level ? RISK_COLOR[level] : UNKNOWN_COLOR)

/** Label for a risk level, "Unknown" when the forecast was missing. */
export const riskLabel = (level: RiskLevelName | null) => (level ? RISK_LABEL[level] : 'Unknown')
