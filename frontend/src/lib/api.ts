/** Generic JSON client for the backend: base URL, JSON encoding and readable error messages. */
import { appConfig } from '../config/appConfig'

export class ApiError extends Error {}

/** Turns DRF error bodies ({"detail": "..."} or {"field": ["..."]}) into one readable message. */
function errorMessageFrom(body: unknown): string {
  if (body && typeof body === 'object') {
    if ('detail' in body) return String(body.detail)
    return Object.entries(body)
      .map(([field, msgs]) => `${field === 'non_field_errors' ? '' : `${field}: `}${([] as unknown[]).concat(msgs).join(' ')}`)
      .join('\n')
  }
  return 'Request failed'
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${appConfig.apiBaseUrl}${path}`, { headers: { 'Content-Type': 'application/json' }, ...init })
  } catch {
    throw new ApiError('Cannot reach the server. Check your connection and try again.')
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(errorMessageFrom(body))
  return body as T
}

export const getJson = <T>(path: string, signal?: AbortSignal) => requestJson<T>(path, { signal })

export const postJson = <T>(path: string, body: unknown) =>
  requestJson<T>(path, { method: 'POST', body: JSON.stringify(body) })
