import client from './client'
import type { LoginResponse, WebAuthnCredential, WebAuthnOptions } from './types'

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/api/auth/login', { username, password })
  return data
}

export async function register(username: string, password: string): Promise<void> {
  await client.post('/api/auth/register', { username, password })
}

export async function setupEncryption(passphrase: string): Promise<void> {
  await client.post('/api/auth/setup-encryption', { passphrase })
}

export async function unlockEncryption(passphrase: string): Promise<void> {
  await client.post('/api/auth/unlock', { passphrase })
}

export async function logout(): Promise<void> {
  await client.post('/api/auth/logout')
}

// ── WebAuthn ─────────────────────────────────────────────────────────────────

export async function webauthnRegisterBegin(): Promise<WebAuthnOptions> {
  const { data } = await client.post<WebAuthnOptions>('/api/auth/webauthn/register/begin')
  return data
}

export async function webauthnRegisterComplete(
  credential: Record<string, unknown>,
  name?: string,
): Promise<WebAuthnCredential> {
  const { data } = await client.post<WebAuthnCredential>(
    '/api/auth/webauthn/register/complete',
    { credential, name },
  )
  return data
}

export async function webauthnAuthBegin(username: string): Promise<WebAuthnOptions> {
  const { data } = await client.post<WebAuthnOptions>(
    '/api/auth/webauthn/authenticate/begin',
    { username },
  )
  return data
}

export async function webauthnAuthComplete(
  credential: Record<string, unknown>,
): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>(
    '/api/auth/webauthn/authenticate/complete',
    { credential },
  )
  return data
}

export async function listWebAuthnCredentials(): Promise<WebAuthnCredential[]> {
  const { data } = await client.get<WebAuthnCredential[]>('/api/auth/webauthn/credentials')
  return data
}

export async function deleteWebAuthnCredential(id: number): Promise<void> {
  await client.delete(`/api/auth/webauthn/credentials/${id}`)
}
