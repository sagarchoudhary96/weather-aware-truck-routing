import { type RefObject, useEffect } from 'react'
import type { MapRef } from 'react-map-gl/maplibre'
import { boundingBox } from '../utils/route.utils'
import type { LonLat, Route, SelectedPoint } from '../types'

/** Fits the map to each new set of routes, and flies to a point picked in the side panel. */
export function useMapCamera(
  mapRef: RefObject<MapRef | null>,
  routes: Route[],
  selectedPoint: SelectedPoint | null,
  selectedPointPosition: LonLat | undefined,
) {
  useEffect(() => {
    if (!routes.length) return
    mapRef.current?.fitBounds(boundingBox(routes.map((r) => r.geometry)), { padding: 70, duration: 900 })
  }, [mapRef, routes])

  useEffect(() => {
    if (selectedPoint?.from !== 'list' || !selectedPointPosition) return
    const map = mapRef.current
    map?.flyTo({ center: selectedPointPosition, zoom: Math.max(map.getZoom(), 8), duration: 700 })
  }, [mapRef, selectedPoint, selectedPointPosition])
}
