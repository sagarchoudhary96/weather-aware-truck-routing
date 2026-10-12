import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { searchPlaces } from '../services/planner.service'
import type { Place } from '../types'
import { useDebouncedValue } from './useDebouncedValue'

const SEARCH_DELAY_MS = 250
const MIN_QUERY_CHARS = 3

/**
 * The text in a place input and the places matching it. Searches once typing pauses,
 * only while the input is open and no place is chosen yet.
 */
export function usePlaceSearch(value: Place | null, isOpen: boolean) {
  const [text, setText] = useState(value?.label ?? '')

  // Show the label when a place is set, including by the parent (e.g. the example trip).
  const [shown, setShown] = useState(value)
  if (value !== shown) {
    setShown(value)
    if (value) setText(value.label)
  }

  const query = useDebouncedValue(text.trim(), SEARCH_DELAY_MS)
  const hasQuery = query.length >= MIN_QUERY_CHARS

  const { data: places = [], isFetching, error } = useQuery({
    queryKey: ['places', query],
    queryFn: ({ signal }) => searchPlaces(query, signal),
    enabled: isOpen && hasQuery && !value,
    staleTime: Infinity,
  })

  return { text, setText, hasQuery, places, isFetching, error }
}
