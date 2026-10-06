import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LEGACY_PIN_KEYS, purgeLegacyPinStorage } from '../legacyPinCleanup'

// Stub localStorage because jsdom doesn't expose it in this setup
const store: Record<string, string> = {}
vi.stubGlobal('localStorage', {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => {
    store[k] = v
  },
  removeItem: (k: string) => {
    delete store[k]
  },
})

describe('purgeLegacyPinStorage', () => {
  beforeEach(() => {
    for (const k of Object.keys(store)) delete store[k]
  })

  it('removes the PIN-wrapped passphrase and its attempt counter', () => {
    for (const key of LEGACY_PIN_KEYS) localStorage.setItem(key, 'x')
    purgeLegacyPinStorage()
    for (const key of LEGACY_PIN_KEYS) expect(localStorage.getItem(key)).toBeNull()
  })

  it('leaves the passkey-wrapped passphrase alone', () => {
    localStorage.setItem('budgie_prf_wrap', 'keep')
    purgeLegacyPinStorage()
    expect(localStorage.getItem('budgie_prf_wrap')).toBe('keep')
  })

  it('does not throw when localStorage is unavailable', () => {
    vi.stubGlobal('localStorage', undefined)
    expect(() => purgeLegacyPinStorage()).not.toThrow()
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => {
        store[k] = v
      },
      removeItem: (k: string) => {
        delete store[k]
      },
    })
  })
})
