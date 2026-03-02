/**
 * Axios HTTP client instance with JWT Bearer interceptor.
 *
 * The token is read from localStorage on every request, so it stays
 * fresh after login/logout without re-configuring the instance.
 */

import axios from 'axios'

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

// On 401, clear the token and redirect to login
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default client
