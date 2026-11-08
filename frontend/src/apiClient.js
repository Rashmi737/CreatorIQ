import axios from 'axios'

const rawBaseUrl = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const apiBaseUrl = rawBaseUrl.endsWith('/api/v1') ? rawBaseUrl : `${rawBaseUrl.replace(/\/+$/, '')}/api/v1`

// Explicit default matching Uvicorn host
const DEFAULT_API_URL = 'http://127.0.0.1:8000/api/v1'

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000,
})

const notifyClient = (title, message, variant = 'error') => {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent('creatoriq:toast', { detail: { title, message, variant } }))
}

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('creatoriq_token')
  if (token) {
    const cleanToken = token.trim().replace(/^["']|["']$/g, '')
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${cleanToken}`
  }
  return config
})

const SILENT_URL_PATTERNS = [
  /\/notifications/,
  /\/analytics\/realtime/,
  /\/stream/,
  /\/health/,
  /\/ready/,
  /\/analytics\/overview/,
]

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail || error.message || 'Unexpected API response'
    const isSilent = error.config?.silent
    const url = error.config?.url || ''
    const isBackgroundPoll = SILENT_URL_PATTERNS.some((pattern) => pattern.test(url))

    if (status === 401) {
      localStorage.removeItem('creatoriq_token')
      localStorage.removeItem('creatoriq_user')
      notifyClient('Session expired', 'Please sign in again to continue.', 'warning')
      const isPublicRoute = ['/', '/login'].includes(window.location.pathname)
      if (!isPublicRoute) window.location.assign('/')
    } else if (!isSilent && !isBackgroundPoll) {
      if (error.code === 'ERR_NETWORK') {
        notifyClient('Network issue', 'Please check your connection and try again.', 'error')
      } else if (status >= 500) {
        notifyClient('Service unavailable', 'The CreatorIQ API is temporarily unavailable.', 'error')
      } else if (detail) {
        notifyClient('Request failed', detail, 'error')
      }
    } else if (isSilent || isBackgroundPoll) {
      console.warn(`[Silent] ${url}: ${detail}`)
    }

    return Promise.reject(error)
  },
)

export { notifyClient }
export default apiClient