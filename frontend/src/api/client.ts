import axios from 'axios'

export const AGENTHUB_OWNER_ID = 'dev_user'

function normalizeBaseUrl(rawValue: string | undefined, fallback: string, suffix: string): string {
  const raw = rawValue?.trim()
  if (!raw) return fallback

  const trimmed = raw.replace(/\/$/, '')
  if (trimmed === suffix || trimmed.endsWith(suffix)) {
    return trimmed
  }

  if (trimmed.startsWith('http://') || trimmed.startsWith('https://') || trimmed.startsWith('ws://') || trimmed.startsWith('wss://')) {
    return `${trimmed}${suffix}`
  }

  return trimmed
}

export const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_HTTP_URL, '/api', '/api')
export const WS_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_WS_URL, '/ws', '/ws')
export const agenthubRequest = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
})

agenthubRequest.interceptors.request.use((config) => {
  const token = localStorage.getItem('x-token')
  if (token) {
    config.headers['x-token'] = token
  }
  return config
})