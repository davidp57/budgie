/**
 * usePinStorage — PIN-based passphrase storage.
 *
 * On unlock, the user may choose to protect their passphrase with a short
 * numeric PIN.  The passphrase is encrypted locally using:
 *   PBKDF2(PIN + device-salt, 100 000 iterations, SHA-256)  →  AES-256-GCM key
 *   AES-GCM-encrypt(passphrase)  →  stored in localStorage (JSON-serialised)
 *
 * localStorage is used instead of IndexedDB for cross-browser persistence,
 * especially Firefox on iOS which aggressively clears IndexedDB on tab close.
 * The stored value is AES-256-GCM ciphertext: safe to keep in localStorage.
 *
 * The PIN is **never** sent to the server.  After 5 wrong attempts the stored
 * data is purged and the user must re-enter their passphrase.
 */

const WRAPPED_KEY = 'budgie_pin_wrap'
const MAX_ATTEMPTS = 5
const ATTEMPTS_KEY = 'budgie_pin_attempts'
const PBKDF2_ITERATIONS = 100_000

interface WrappedPassphrase {
  salt: number[] // 32 bytes
  iv: number[] // 12 bytes — AES-GCM nonce
  ciphertext: number[] // variable
}

async function deriveWrappingKey(pin: string, salt: Uint8Array<ArrayBuffer>): Promise<CryptoKey> {
  const enc = new TextEncoder()
  const keyMaterial = await crypto.subtle.importKey('raw', enc.encode(pin), 'PBKDF2', false, [
    'deriveKey',
  ])
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: PBKDF2_ITERATIONS, hash: 'SHA-256' },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  )
}

export function usePinStorage() {
  function hasStoredPassphrase(): Promise<boolean> {
    return Promise.resolve(localStorage.getItem(WRAPPED_KEY) !== null)
  }

  async function storePassphrase(pin: string, passphrase: string): Promise<void> {
    const salt = crypto.getRandomValues(new Uint8Array(32))
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const key = await deriveWrappingKey(pin, salt)
    const enc = new TextEncoder()
    const ciphertext = new Uint8Array(
      await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, enc.encode(passphrase)),
    )
    const wrapped: WrappedPassphrase = {
      salt: Array.from(salt),
      iv: Array.from(iv),
      ciphertext: Array.from(ciphertext),
    }
    localStorage.setItem(WRAPPED_KEY, JSON.stringify(wrapped))
    localStorage.setItem(ATTEMPTS_KEY, '0')
  }

  /**
   * Try to decrypt the stored passphrase with the supplied PIN.
   *
   * @returns The plaintext passphrase on success, `null` on wrong PIN or no data.
   */
  async function retrievePassphrase(pin: string): Promise<string | null> {
    const attempts = parseInt(localStorage.getItem(ATTEMPTS_KEY) ?? '0', 10)
    if (attempts >= MAX_ATTEMPTS) {
      clearStoredPassphrase()
      return null
    }

    const raw = localStorage.getItem(WRAPPED_KEY)
    if (!raw) return null

    let wrapped: WrappedPassphrase
    try {
      wrapped = JSON.parse(raw) as WrappedPassphrase
    } catch {
      return null
    }

    const salt = new Uint8Array(wrapped.salt)
    const iv = new Uint8Array(wrapped.iv)
    const ciphertext = new Uint8Array(wrapped.ciphertext)

    try {
      const key = await deriveWrappingKey(pin, salt)
      const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ciphertext)
      localStorage.setItem(ATTEMPTS_KEY, '0')
      return new TextDecoder().decode(plain)
    } catch {
      const newAttempts = attempts + 1
      localStorage.setItem(ATTEMPTS_KEY, String(newAttempts))
      if (newAttempts >= MAX_ATTEMPTS) {
        clearStoredPassphrase()
      }
      return null
    }
  }

  function clearStoredPassphrase(): void {
    localStorage.removeItem(WRAPPED_KEY)
    localStorage.removeItem(ATTEMPTS_KEY)
  }

  function getRemainingAttempts(): number {
    const attempts = parseInt(localStorage.getItem(ATTEMPTS_KEY) ?? '0', 10)
    return Math.max(0, MAX_ATTEMPTS - attempts)
  }

  return {
    hasStoredPassphrase,
    storePassphrase,
    retrievePassphrase,
    clearStoredPassphrase,
    getRemainingAttempts,
  }
}
