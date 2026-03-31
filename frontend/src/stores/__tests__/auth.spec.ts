import { describe, it, expect, vi, beforeEach, beforeAll, afterAll } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  logout: vi.fn().mockResolvedValue(undefined),
  setupEncryption: vi.fn().mockResolvedValue(undefined),
  unlockEncryption: vi.fn().mockResolvedValue(undefined),
  webauthnRegisterBegin: vi.fn(),
  webauthnRegisterComplete: vi.fn(),
  webauthnAuthBegin: vi.fn(),
  webauthnAuthComplete: vi.fn(),
  listWebAuthnCredentials: vi.fn().mockResolvedValue([]),
  deleteWebAuthnCredential: vi.fn(),
}))

// Stub localStorage/sessionStorage because jsdom doesn't expose them in this setup
let _local: Record<string, string> = {}
let _session: Record<string, string> = {}

const localStorageMock = {
  getItem: (key: string) => _local[key] ?? null,
  setItem: (key: string, value: string) => { _local[key] = value },
  removeItem: (key: string) => { delete _local[key] },
}
const sessionStorageMock = {
  getItem: (key: string) => _session[key] ?? null,
  setItem: (key: string, value: string) => { _session[key] = value },
  removeItem: (key: string) => { delete _session[key] },
}

beforeAll(() => {
  vi.stubGlobal('localStorage', localStorageMock)
  vi.stubGlobal('sessionStorage', sessionStorageMock)
})

afterAll(() => {
  vi.unstubAllGlobals()
})

describe('useAuthStore', () => {
  beforeEach(() => {
    _local = {}
    _session = {}
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('setupEncryption()', () => {
    it('sets is_encrypted and needs_encryption_setup=false in localStorage', async () => {
      const store = useAuthStore()
      await store.setupEncryption('my-passphrase')
      expect(localStorage.getItem('needs_encryption_setup')).toBe('false')
      expect(localStorage.getItem('is_encrypted')).toBe('true')
    })

    it('sets encryption_unlocked=true in sessionStorage', async () => {
      const store = useAuthStore()
      await store.setupEncryption('my-passphrase')
      expect(sessionStorage.getItem('encryption_unlocked')).toBe('true')
    })

    it('updates reactive store state', async () => {
      const store = useAuthStore()
      await store.setupEncryption('my-passphrase')
      expect(store.needsEncryptionSetup).toBe(false)
      expect(store.isEncrypted).toBe(true)
    })
  })

  describe('unlock()', () => {
    it('sets encryption_unlocked=true in sessionStorage', async () => {
      const store = useAuthStore()
      await store.unlock('my-passphrase')
      expect(sessionStorage.getItem('encryption_unlocked')).toBe('true')
    })

    it('stores the passphrase in memory only', async () => {
      const store = useAuthStore()
      await store.unlock('secret-phrase')
      expect(store.sessionPassphrase).toBe('secret-phrase')
      // Never persisted to localStorage
      expect(localStorage.getItem('session_passphrase')).toBeNull()
    })
  })

  describe('login()', () => {
    it('clears encryption_unlocked from sessionStorage on login', async () => {
      sessionStorage.setItem('encryption_unlocked', 'true')
      const { login } = await import('@/api/auth')
      vi.mocked(login).mockResolvedValueOnce({
        access_token: 'tok',
        token_type: 'bearer',
        needs_encryption_setup: false,
        is_encrypted: false,
      })
      const store = useAuthStore()
      await store.login('alice', 'pw')
      expect(sessionStorage.getItem('encryption_unlocked')).toBeNull()
    })

    it('persists access_token and username to localStorage', async () => {
      const { login } = await import('@/api/auth')
      vi.mocked(login).mockResolvedValueOnce({
        access_token: 'my-token',
        token_type: 'bearer',
        needs_encryption_setup: false,
        is_encrypted: false,
      })
      const store = useAuthStore()
      await store.login('alice', 'pw')
      expect(localStorage.getItem('access_token')).toBe('my-token')
      expect(localStorage.getItem('username')).toBe('alice')
    })
  })

  describe('logout()', () => {
    it('removes all auth and encryption keys from storage', () => {
      localStorage.setItem('access_token', 'tok')
      localStorage.setItem('username', 'alice')
      localStorage.setItem('needs_encryption_setup', 'false')
      localStorage.setItem('is_encrypted', 'true')
      sessionStorage.setItem('encryption_unlocked', 'true')
      const store = useAuthStore()
      store.logout()
      expect(localStorage.getItem('access_token')).toBeNull()
      expect(localStorage.getItem('username')).toBeNull()
      expect(localStorage.getItem('needs_encryption_setup')).toBeNull()
      expect(localStorage.getItem('is_encrypted')).toBeNull()
      expect(sessionStorage.getItem('encryption_unlocked')).toBeNull()
    })

    it('resets reactive state', () => {
      localStorage.setItem('access_token', 'tok')
      localStorage.setItem('username', 'alice')
      const store = useAuthStore()
      store.logout()
      expect(store.token).toBeNull()
      expect(store.username).toBeNull()
      expect(store.isAuthenticated).toBe(false)
    })
  })
})
