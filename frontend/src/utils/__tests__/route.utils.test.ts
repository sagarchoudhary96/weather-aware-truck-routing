import { describe, expect, it } from 'vitest'
import type { Route } from '../../types'
import { boundingBox, truckPositionAt } from '../route.utils'

describe('truckPositionAt', () => {
  const track: Route['track'] = [
    [0, -100, 40],
    [600, -99, 40],
    [1200, -99, 40], // parked
    [1800, -98, 40],
  ]
  it('returns the recorded sample on a 10-minute step', () => {
    expect(truckPositionAt(track, 600)).toEqual([-99, 40])
  })
  it('blends between samples and holds while parked', () => {
    expect(truckPositionAt(track, 300)).toEqual([-99.5, 40])
    expect(truckPositionAt(track, 900)).toEqual([-99, 40])
    expect(truckPositionAt(track, 1500)).toEqual([-98.5, 40])
  })
  it('clamps outside the track', () => {
    expect(truckPositionAt(track, -10)).toEqual([-100, 40])
    expect(truckPositionAt(track, 1e6)).toEqual([-98, 40])
  })
})

describe('boundingBox', () => {
  it('covers every point of every line', () => {
    const box = boundingBox([
      [
        [-100, 40],
        [-98, 41],
      ],
      [[-101, 39.5]],
    ])
    expect(box).toEqual([
      [-101, 39.5],
      [-98, 41],
    ])
  })
})
