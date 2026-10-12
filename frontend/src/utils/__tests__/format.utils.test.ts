import { describe, expect, it } from 'vitest'
import { formatDuration, toDateTimeInputValue } from '../format.utils'

describe('format', () => {
  it('formats durations', () => {
    expect(formatDuration(45 * 60)).toBe('45m')
    expect(formatDuration(9.5 * 3600)).toBe('9h 30m')
    expect(formatDuration(22 * 3600 + 5 * 60)).toBe('22h 05m')
  })
  it('builds datetime-local values', () => {
    expect(toDateTimeInputValue(new Date(2026, 9, 13, 6, 5))).toBe('2026-10-13T06:05')
  })
})
