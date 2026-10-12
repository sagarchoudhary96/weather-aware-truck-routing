import { RISK_COLOR, RISK_LABEL, RISK_LEVELS } from '../constants/risk.constants'

export function RiskLegend() {
  return (
    <div className="legend">
      <div className="legend-title">Risk</div>
      {RISK_LEVELS.map((level) => (
        <div key={level} className="legend-row">
          <span className="swatch" style={{ background: RISK_COLOR[level] }} />
          {RISK_LABEL[level]}
        </div>
      ))}
      <div className="legend-note">
        Heatmap: load-aware risk at the slider time (Low is clear). Dots: risk at the truck’s arrival time.
      </div>
    </div>
  )
}
