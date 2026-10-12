import { useEffect, useRef, useState } from 'react'

const PLAYBACK_HOURS_PER_SECOND = 4

/** Plays the slider forward at 4 h per second and stops at `maxHour`. */
export function usePlayback(hour: number, maxHour: number, onChange: (hour: number) => void) {
  const [playing, setPlaying] = useState(false)
  const hourRef = useRef(hour)
  useEffect(() => {
    hourRef.current = hour
  }, [hour])

  useEffect(() => {
    if (!playing) return
    let frame = 0
    let last = performance.now()
    const tick = (now: number) => {
      const next = Math.min(hourRef.current + ((now - last) / 1000) * PLAYBACK_HOURS_PER_SECOND, maxHour)
      last = now
      onChange(next)
      if (next >= maxHour) setPlaying(false)
      else frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing, maxHour, onChange])

  const togglePlay = () => {
    if (!playing && hour >= maxHour) onChange(0) // replay from the start
    setPlaying(!playing)
  }

  return { playing, togglePlay, stop: () => setPlaying(false) }
}
