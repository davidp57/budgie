/**
 * useWebAuthn — thin wrapper around the Web Credentials API.
 *
 * Handles base64url ↔ ArrayBuffer conversions so call sites only
 * deal with plain JS objects and strings.
 */

// ── Encoding helpers ──────────────────────────────────────────────────────────

function base64urlToUint8Array(b64url: string): Uint8Array<ArrayBuffer> {
  const pad = '='.repeat((4 - (b64url.length % 4)) % 4)
  const base64 = b64url.replace(/-/g, '+').replace(/_/g, '/') + pad
  const binary = atob(base64)
  const result = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) result[i] = binary.charCodeAt(i)
  return result
}

function arrayBufferToBase64url(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf)
  let binary = ''
  bytes.forEach((b) => (binary += String.fromCharCode(b)))
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

// ── Registration ──────────────────────────────────────────────────────────────

interface ServerRegistrationOptions {
  challenge: string
  rp: { id: string; name: string }
  user: { id: string; name: string; displayName: string }
  pubKeyCredParams: PublicKeyCredentialParameters[]
  // other optional fields are passed through as-is
  [key: string]: unknown
}

/**
 * Run the browser side of WebAuthn credential registration.
 *
 * @param serverOptions - JSON options object from `POST /register/begin`.
 * @returns A JSON-serialisable object ready to `POST /register/complete`.
 */
export async function createPasskey(
  serverOptions: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const opts = serverOptions as ServerRegistrationOptions

  const publicKey: PublicKeyCredentialCreationOptions = {
    ...(serverOptions as object),
    challenge: base64urlToUint8Array(opts.challenge),
    user: {
      ...opts.user,
      id: base64urlToUint8Array(opts.user.id),
    },
    excludeCredentials: (
      (opts.excludeCredentials as Array<{ id: string; type: string }> | undefined) ?? []
    ).map((c) => ({
      ...c,
      id: base64urlToUint8Array(c.id),
    })),
  } as unknown as PublicKeyCredentialCreationOptions

  const credential = (await navigator.credentials.create({
    publicKey,
  })) as PublicKeyCredential | null

  if (!credential) throw new Error('No credential returned from browser')

  const response = credential.response as AuthenticatorAttestationResponse
  return {
    id: credential.id,
    rawId: arrayBufferToBase64url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: arrayBufferToBase64url(response.clientDataJSON),
      attestationObject: arrayBufferToBase64url(response.attestationObject),
    },
  }
}

// ── Authentication ─────────────────────────────────────────────────────────────

/**
 * Fixed PRF eval input shared across all Budgie clients.
 *
 * Each passkey (credential) produces a unique 32-byte HMAC-SHA-256 output for
 * this constant salt, so using a single application-level constant is safe.
 */
export const PRF_EVAL_INPUT: Uint8Array = new TextEncoder().encode('budgie-passphrase-v1')

interface ServerAuthOptions {
  challenge: string
  allowCredentials?: Array<{ id: string; type: string }>
  [key: string]: unknown
}

interface PrfExtensionOutput {
  results?: {
    first?: ArrayBuffer
  }
}

/**
 * Run the browser side of WebAuthn authentication.
 *
 * @param serverOptions - JSON options object from `POST /authenticate/begin`.
 * @param requestPrf - When `true`, request the PRF extension so the caller can
 *   use the output to wrap/unwrap the encryption passphrase locally.
 * @returns An object containing the JSON-serialisable assertion for the server
 *   and, when `requestPrf` is `true`, the raw PRF output (or `null` if the
 *   authenticator does not support PRF).
 */
export async function getPasskey(
  serverOptions: Record<string, unknown>,
  requestPrf = false,
): Promise<{ credential: Record<string, unknown>; prfOutput: ArrayBuffer | null }> {
  const opts = serverOptions as ServerAuthOptions

  const publicKey: PublicKeyCredentialRequestOptions = {
    ...(serverOptions as object),
    challenge: base64urlToUint8Array(opts.challenge),
    allowCredentials: (opts.allowCredentials ?? []).map((c) => ({
      ...c,
      id: base64urlToUint8Array(c.id),
    })),
    ...(requestPrf ? { extensions: { prf: { eval: { first: PRF_EVAL_INPUT } } } } : {}),
  } as PublicKeyCredentialRequestOptions

  const assertion = (await navigator.credentials.get({
    publicKey,
  })) as PublicKeyCredential | null

  if (!assertion) throw new Error('No assertion returned from browser')

  // Extract PRF output when requested (null if authenticator does not support it)
  let prfOutput: ArrayBuffer | null = null
  if (requestPrf) {
    const ext = assertion.getClientExtensionResults() as Record<string, unknown>
    const prf = ext['prf'] as PrfExtensionOutput | undefined
    prfOutput = prf?.results?.first ?? null
  }

  const response = assertion.response as AuthenticatorAssertionResponse
  const credential: Record<string, unknown> = {
    id: assertion.id,
    rawId: arrayBufferToBase64url(assertion.rawId),
    type: assertion.type,
    response: {
      clientDataJSON: arrayBufferToBase64url(response.clientDataJSON),
      authenticatorData: arrayBufferToBase64url(response.authenticatorData),
      signature: arrayBufferToBase64url(response.signature),
      userHandle: response.userHandle ? arrayBufferToBase64url(response.userHandle) : null,
    },
  }
  return { credential, prfOutput }
}

export function isWebAuthnSupported(): boolean {
  return typeof window.PublicKeyCredential !== 'undefined'
}
