import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth'

// Mock the auth API module
vi.mock('@/api/auth', () => ({
  login: vi.fn().mockResolvedValue({ access_token: 'fake-token', token_type: 'bearer' }),
  logout: vi.fn().mockResolvedValue(undefined),
}))

// Mock localStorage
const storageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
vi.stubGlobal('localStorage', storageMock)

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    storageMock.clear()
  })

  it('starts unauthenticated', () => {
    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.token).toBeNull()
  })

  it('sets token and username on login', async () => {
    const auth = useAuthStore()
    await auth.login('alice', 'secret')
    expect(auth.token).toBe('fake-token')
    expect(auth.username).toBe('alice')
    expect(auth.isAuthenticated).toBe(true)
  })

  it('persists token to localStorage on login', async () => {
    const auth = useAuthStore()
    await auth.login('alice', 'secret')
    expect(localStorage.getItem('access_token')).toBe('fake-token')
    expect(localStorage.getItem('username')).toBe('alice')
  })

  it('clears token on logout', async () => {
    const auth = useAuthStore()
    await auth.login('alice', 'secret')
    auth.logout()
    expect(auth.token).toBeNull()
    expect(auth.isAuthenticated).toBe(false)
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})
