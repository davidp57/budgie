/**
 * usePrfStorage — WebAuthn-PRF-based passphrase storage.
 *
 * After a successful passkey authentication, the browser's PRF extension
 * provides a 32-byte HMAC-SHA-256 secret unique to the credential.  This
 * secret is imported directly as an AES-256-GCM key and used to wrap the
 * encryption passphrase locally, enabling one-tap unlock.
 *
 * Requirements:
 *   - HTTPS / localhost
 *   - Browser support: Chrome 116+, Safari 17.5+ (Firefox: not yet)
 *   - A compatible authenticator (platform authenticators on modern OS)
 *
 * The passphrase is **never** sent to the server in this flow; the PRF secret
 * never leaves the authenticator.  Falls back to PIN or passphrase when PRF
 * is unavailable.
 */

const WRAPPED_KEY = 'budgie_prf_wrap'

interface PrfWrappedPassphrase {
  iv: number[] // 12 bytes — AES-GCM nonce
  ciphertext: number[] // variable
}

async function keyFromPrfOutput(prfOutput: ArrayBuffer): Promise<CryptoKey> {
  return crypto.subtle.importKey('raw', prfOutput, { name: 'AES-GCM', length: 256 }, false, [
    'encrypt',
    'decrypt',
  ])
}

export function usePrfStorage() {
  /** Returns true if a PRF-wrapped passphrase is present in localStorage. */
  function hasPrfPassphrase(): boolean {
    return localStorage.getItem(WRAPPED_KEY) !== null
  }

  /**
   * Encrypt and persist the passphrase using the PRF output as an AES-256-GCM key.
   *
   * @param prfOutput - 32-byte PRF output from `getClientExtensionResults().prf.results.first`.
   * @param passphrase - The plaintext encryption passphrase to wrap.
   */
  async function storePrfPassphrase(prfOutput: ArrayBuffer, passphrase: string): Promise<void> {
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const key = await keyFromPrfOutput(prfOutput)
    const enc = new TextEncoder()
    const ciphertext = new Uint8Array(
      await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, enc.encode(passphrase)),
    )
    const wrapped: PrfWrappedPassphrase = {
      iv: Array.from(iv),
      ciphertext: Array.from(ciphertext),
    }
    localStorage.setItem(WRAPPED_KEY, JSON.stringify(wrapped))
  }

  /**
   * Try to decrypt the stored passphrase using the provided PRF output.
   *
   * @param prfOutput - 32-byte PRF output from a new passkey assertion.
   * @returns The plaintext passphrase on success, or `null` if no data is
   *   stored or decryption fails (wrong credential / data corrupted).
   */
  async function retrievePrfPassphrase(prfOutput: ArrayBuffer): Promise<string | null> {
    const raw = localStorage.getItem(WRAPPED_KEY)
    if (!raw) return null

    let wrapped: PrfWrappedPassphrase
    try {
      wrapped = JSON.parse(raw) as PrfWrappedPassphrase
    } catch {
      return null
    }

    const iv = new Uint8Array(wrapped.iv)
    const ciphertext = new Uint8Array(wrapped.ciphertext)

    try {
      const key = await keyFromPrfOutput(prfOutput)
      const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ciphertext)
      return new TextDecoder().decode(plain)
    } catch {
      return null
    }
  }

  /** Remove the PRF-wrapped passphrase from localStorage. */
  function clearPrfPassphrase(): void {
    localStorage.removeItem(WRAPPED_KEY)
  }

  return {
    hasPrfPassphrase,
    storePrfPassphrase,
    retrievePrfPassphrase,
    clearPrfPassphrase,
  }
}
