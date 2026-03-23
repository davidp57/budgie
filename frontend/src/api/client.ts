/**
 * Axios HTTP client instance with JWT Bearer interceptor and global
 * error toast notifications.
 *
 * The token is read from localStorage on every request, so it stays
 * fresh after login/logout without re-configuring the instance.
 */

import axios from 'axios'
import { useToastStore } from '@/stores/toast'

const client = axios.create({
  baseURL: '/',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Attach Authorization header if a token is stored
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On 401: clear token + show toast. On other errors: show toast.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      // Show auth error via toast instead of hard redirect
      try {
        const toast = useToastStore()
        toast.error('Non authentifié — vérifiez la configuration du serveur')
      } catch {
        // toast store not yet available
      }
    } else if (error.response) {
      // Only show a toast for non-401 server errors; callers can still
      // catch the error for their own flow (e.g. form validation).
      const status: number = error.response.status as number
      // Skip 422 (handled locally by forms) and 409 (handled by import)
      if (status !== 422 && status !== 409) {
        try {
          const toast = useToastStore()
          const detail = error.response.data?.detail
          const message =
            typeof detail === 'string'
              ? detail
              : `Request failed (${status})`
          toast.error(message)
        } catch {
          // toast store not yet available (e.g. during SSR or test)
        }
      }
    }
    return Promise.reject(error)
  },
)

export default client
