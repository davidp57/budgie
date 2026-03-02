/**
 * Auth Pinia store — handles JWT token persistence and user session.
 */

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { login as apiLogin } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const username = ref<string | null>(localStorage.getItem('username'))

  const isAuthenticated = computed(() => token.value !== null)

  async function login(user: string, password: string): Promise<void> {
    const response = await apiLogin(user, password)
    token.value = response.access_token
    username.value = user
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('username', user)
  }

  function logout(): void {
    token.value = null
    username.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('username')
  }

  return { token, username, isAuthenticated, login, logout }
})
