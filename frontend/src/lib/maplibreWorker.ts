// Vite relocates bundled modules, which breaks MapLibre's default worker lookup, point it at a bundled copy.
import { setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

setWorkerUrl(workerUrl)
