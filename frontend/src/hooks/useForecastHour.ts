import { useCallback, useState } from 'react'

/** The slider hour. It's tied to the plan it was set for, so a new plan starts back at T+0. */
export function useForecastHour(planVersion: number) {
  const [slider, setSlider] = useState({ planVersion, hour: 0 })
  const hour = slider.planVersion === planVersion ? slider.hour : 0
  const setHour = useCallback((h: number) => setSlider({ planVersion, hour: h }), [planVersion])
  return [hour, setHour] as const
}
