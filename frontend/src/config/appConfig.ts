/** The single place that reads environment variables. Import settings from here, never from import.meta.env. */
export const appConfig = {
  /** Backend base URL, without a trailing slash. Set VITE_API_URL at build time (e.g. on Vercel). */
  apiBaseUrl: (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, ''),
} as const
