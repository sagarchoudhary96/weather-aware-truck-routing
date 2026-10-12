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
        Heatmap: worst risk forecast nearby at the slider time (Low is clear). Route and dots: risk on the road when the truck gets there.
      </div>
    </div>
  )
}
