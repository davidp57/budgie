/**
 * Auth Pinia store — handles JWT token persistence and user session.
 */

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  login as apiLogin,
  logout as apiLogout,
  setupEncryption as apiSetupEncryption,
  unlockEncryption as apiUnlock,
  webauthnRegisterBegin as apiWebauthnRegisterBegin,
  webauthnRegisterComplete as apiWebauthnRegisterComplete,
  webauthnAuthBegin as apiWebauthnAuthBegin,
  webauthnAuthComplete as apiWebauthnAuthComplete,
  listWebAuthnCredentials as apiListWebAuthnCredentials,
  deleteWebAuthnCredential as apiDeleteWebAuthnCredential,
} from '@/api/auth'
import type { WebAuthnCredential } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const username = ref<string | null>(localStorage.getItem('username'))
  const needsEncryptionSetup = ref<boolean>(
    localStorage.getItem('needs_encryption_setup') === 'true',
  )
  const isEncrypted = ref<boolean>(localStorage.getItem('is_encrypted') === 'true')
  /** Passphrase held in memory for the session only (never persisted). */
  const sessionPassphrase = ref<string | null>(null)
  /** Registered passkeys for the current user (loaded on demand). */
  const webauthnCredentials = ref<WebAuthnCredential[]>([])

  const isAuthenticated = computed(() => token.value !== null)
  const isUnlocked = computed(
    () => !isEncrypted.value || sessionPassphrase.value !== null,
  )

  async function login(user: string, password: string): Promise<void> {
    const response = await apiLogin(user, password)
    token.value = response.access_token
    username.value = user
    needsEncryptionSetup.value = response.needs_encryption_setup
    isEncrypted.value = response.is_encrypted
    sessionPassphrase.value = null
    sessionStorage.removeItem('encryption_unlocked')
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('username', user)
    localStorage.setItem('needs_encryption_setup', String(response.needs_encryption_setup))
    localStorage.setItem('is_encrypted', String(response.is_encrypted))
  }

  async function setupEncryption(passphrase: string): Promise<void> {
    await apiSetupEncryption(passphrase)
    sessionPassphrase.value = passphrase
    needsEncryptionSetup.value = false
    isEncrypted.value = true
    localStorage.setItem('needs_encryption_setup', 'false')
    localStorage.setItem('is_encrypted', 'true')
    sessionStorage.setItem('encryption_unlocked', 'true')
  }

  async function unlock(passphrase: string): Promise<void> {
    await apiUnlock(passphrase)
    sessionPassphrase.value = passphrase
    sessionStorage.setItem('encryption_unlocked', 'true')
  }

  function logout(): void {
    // Best-effort: notify the backend to purge the session key from RAM.
    apiLogout().catch(() => undefined)
    token.value = null
    username.value = null
    needsEncryptionSetup.value = false
    isEncrypted.value = false
    sessionPassphrase.value = null
    webauthnCredentials.value = []
    localStorage.removeItem('access_token')
    localStorage.removeItem('username')
    localStorage.removeItem('needs_encryption_setup')
    localStorage.removeItem('is_encrypted')
    sessionStorage.removeItem('encryption_unlocked')
  }

  // ── WebAuthn ──────────────────────────────────────────────────────────────

  /**
   * Start passkey registration; returns raw options to pass to
   * `navigator.credentials.create()`.
   */
  async function webauthnRegisterBegin(): Promise<Record<string, unknown>> {
    const { options } = await apiWebauthnRegisterBegin()
    return options
  }

  /**
   * Complete passkey registration after `navigator.credentials.create()`.
   * Saves the new credential and refreshes the local list.
   */
  async function webauthnRegisterComplete(
    credential: Record<string, unknown>,
    name?: string,
  ): Promise<void> {
    const saved = await apiWebauthnRegisterComplete(credential, name)
    webauthnCredentials.value.push(saved)
  }

  /**
   * Start passkey authentication for `user`; returns challenge options
   * to pass to `navigator.credentials.get()`.
   */
  async function webauthnAuthBegin(user: string): Promise<Record<string, unknown>> {
    const { options } = await apiWebauthnAuthBegin(user)
    return options
  }

  /**
   * Complete passkey authentication after `navigator.credentials.get()`.
   * Stores the JWT exactly like a password login.
   */
  async function webauthnAuthComplete(
    user: string,
    credential: Record<string, unknown>,
  ): Promise<void> {
    const response = await apiWebauthnAuthComplete(credential)
    token.value = response.access_token
    username.value = user
    needsEncryptionSetup.value = response.needs_encryption_setup
    isEncrypted.value = response.is_encrypted
    sessionPassphrase.value = null
    sessionStorage.removeItem('encryption_unlocked')
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('username', user)
    localStorage.setItem('needs_encryption_setup', String(response.needs_encryption_setup))
    localStorage.setItem('is_encrypted', String(response.is_encrypted))
  }

  /** Load all registered passkeys for the current user. */
  async function loadWebAuthnCredentials(): Promise<void> {
    webauthnCredentials.value = await apiListWebAuthnCredentials()
  }

  /** Remove a registered passkey by its database ID. */
  async function deleteWebAuthnCredential(id: number): Promise<void> {
    await apiDeleteWebAuthnCredential(id)
    webauthnCredentials.value = webauthnCredentials.value.filter((c) => c.id !== id)
  }

  return {
    token,
    username,
    needsEncryptionSetup,
    isEncrypted,
    sessionPassphrase,
    webauthnCredentials,
    isAuthenticated,
    isUnlocked,
    login,
    setupEncryption,
    unlock,
    logout,
    webauthnRegisterBegin,
    webauthnRegisterComplete,
    webauthnAuthBegin,
    webauthnAuthComplete,
    loadWebAuthnCredentials,
    deleteWebAuthnCredential,
  }
})
