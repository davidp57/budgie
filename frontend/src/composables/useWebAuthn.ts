/**
 * useWebAuthn — thin wrapper around the Web Credentials API.
 *
 * Handles base64url ↔ ArrayBuffer conversions so call sites only
 * deal with plain JS objects and strings.
 */

// ── Encoding helpers ──────────────────────────────────────────────────────────

function base64urlToUint8Array(b64url: string): Uint8Array {
  const pad = '='.repeat((4 - (b64url.length % 4)) % 4)
  const base64 = b64url.replace(/-/g, '+').replace(/_/g, '/') + pad
  const binary = atob(base64)
  return new Uint8Array(binary.length).map((_, i) => binary.charCodeAt(i))
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
  } as PublicKeyCredentialCreationOptions

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

interface ServerAuthOptions {
  challenge: string
  allowCredentials?: Array<{ id: string; type: string }>
  [key: string]: unknown
}

/**
 * Run the browser side of WebAuthn authentication.
 *
 * @param serverOptions - JSON options object from `POST /authenticate/begin`.
 * @returns A JSON-serialisable assertion object ready to `POST /authenticate/complete`.
 */
export async function getPasskey(
  serverOptions: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const opts = serverOptions as ServerAuthOptions

  const publicKey: PublicKeyCredentialRequestOptions = {
    ...(serverOptions as object),
    challenge: base64urlToUint8Array(opts.challenge),
    allowCredentials: (opts.allowCredentials ?? []).map((c) => ({
      ...c,
      id: base64urlToUint8Array(c.id),
    })),
  } as PublicKeyCredentialRequestOptions

  const assertion = (await navigator.credentials.get({
    publicKey,
  })) as PublicKeyCredential | null

  if (!assertion) throw new Error('No assertion returned from browser')

  const response = assertion.response as AuthenticatorAssertionResponse
  return {
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
}

export function isWebAuthnSupported(): boolean {
  return typeof window.PublicKeyCredential !== 'undefined'
}
