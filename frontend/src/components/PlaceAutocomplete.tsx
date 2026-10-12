import { useId, useState } from 'react'
import { usePlaceSearch } from '../hooks/usePlaceSearch'
import type { Place } from '../types'

interface Props {
  label: string
  value: Place | null
  onChange: (place: Place | null) => void
}

export function PlaceAutocomplete({ label, value, onChange }: Props) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(0)
  const { text, setText, hasQuery, places, isFetching, error } = usePlaceSearch(value, open)

  const selectPlace = (place: Place) => {
    onChange(place)
    setOpen(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || !places.length) return
    if (e.key === 'ArrowDown') setHighlighted((i) => Math.min(i + 1, places.length - 1))
    else if (e.key === 'ArrowUp') setHighlighted((i) => Math.max(i - 1, 0))
    else if (e.key === 'Enter') selectPlace(places[highlighted])
    else if (e.key === 'Escape') setOpen(false)
    else return
    e.preventDefault()
  }

  return (
    <div className="field place-input">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        value={text}
        placeholder="City or address"
        autoComplete="off"
        role="combobox"
        aria-expanded={open && places.length > 0}
        aria-controls={`${id}-list`}
        onChange={(e) => {
          setText(e.target.value)
          setOpen(true)
          setHighlighted(0)
          if (value) onChange(null)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={handleKeyDown}
      />
      {open && hasQuery && !value && (
        <ul className="suggestions" id={`${id}-list`} role="listbox">
          {places.map((p, i) => (
            <li
              key={`${p.lat},${p.lon}`}
              role="option"
              aria-selected={i === highlighted}
              className={i === highlighted ? 'active' : ''}
              onMouseDown={() => selectPlace(p)}
            >
              {p.label}
            </li>
          ))}
          {!places.length && (
            <li className="muted">{error ? error.message : isFetching ? 'Searching…' : 'No matches'}</li>
          )}
        </ul>
      )}
    </div>
  )
}
