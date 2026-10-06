<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { shouldOfferPrfSetup, usePrfStorage } from '@/composables/usePrfStorage'
import { getPasskey, isWebAuthnSupported } from '@/composables/useWebAuthn'

function extractError(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}

const auth = useAuthStore()
const router = useRouter()
const prf = usePrfStorage()

// ── UI state ──────────────────────────────────────────────────────────────────
/**
 * 'passphrase' — standard passphrase entry
 * 'prf'        — tap to unlock with passkey (PRF-wrapped passphrase stored)
 * 'prf-setup'  — offer passkey unlock setup after a passphrase unlock, when
 *                the account has a passkey but no PRF output is in the store
 */
type UnlockMode = 'passphrase' | 'prf' | 'prf-setup'
const mode = ref<UnlockMode>('passphrase')

const passphrase = ref('')
const error = ref('')
const loading = ref(false)

/** Passkey unlock needs crypto.subtle, only available on HTTPS / localhost. */
const cryptoAvailable = typeof window !== 'undefined' && !!window.crypto?.subtle

const hasPrfStored = ref(false)

onMounted(async () => {
  if (!cryptoAvailable) return
  hasPrfStored.value = prf.hasPrfPassphrase()

  // Seamless PRF unlock: passkey was just used to log in and PRF output is in store
  if (hasPrfStored.value && auth.prfOutput) {
    await autoPrfUnlock(auth.prfOutput)
    return
  }
  if (hasPrfStored.value) {
    mode.value = 'prf'
  }
})

// ── Passphrase unlock ─────────────────────────────────────────────────────────
async function submitPassphrase(): Promise<void> {
  error.value = ''
  loading.value = true
  try {
    await auth.unlock(passphrase.value)

    // If we already have a PRF output from the passkey login (in-memory),
    // save it silently — no second authenticator gesture needed.
    if (cryptoAvailable && !hasPrfStored.value && auth.prfOutput) {
      try {
        await prf.storePrfPassphrase(auth.prfOutput, passphrase.value)
      } catch {
        // Save failed (not HTTPS, etc.) — the passphrase stays the way in
      }
    } else if (await canOfferPrfSetup()) {
      mode.value = 'prf-setup'
      return
    }
    await router.push('/')
  } catch (err) {
    error.value = extractError(err, 'Incorrect passphrase.')
  } finally {
    loading.value = false
  }
}

/** Whether to offer passkey unlock now that the passphrase is in memory. */
async function canOfferPrfSetup(): Promise<boolean> {
  const supported = cryptoAvailable && isWebAuthnSupported()
  if (!supported || hasPrfStored.value || prf.isOfferDismissed()) return false
  try {
    await auth.loadWebAuthnCredentials()
  } catch {
    return false // Non-critical — never block the unlock on this offer
  }
  return shouldOfferPrfSetup({
    supported,
    hasPrfStored: hasPrfStored.value,
    passkeyCount: auth.webauthnCredentials.length,
    dismissed: prf.isOfferDismissed(),
  })
}

function declinePrfSetup(): void {
  prf.dismissOffer()
  void router.push('/')
}

// ── PRF auto-unlock (called on mount when auth.prfOutput is available) ────────
async function autoPrfUnlock(prfOut: ArrayBuffer): Promise<void> {
  loading.value = true
  try {
    const stored = await prf.retrievePrfPassphrase(prfOut)
    if (!stored) {
      // Credential changed or data corrupted — fall back gracefully
      prf.clearPrfPassphrase()
      hasPrfStored.value = false
      mode.value = 'passphrase'
      return
    }
    await auth.unlock(stored)
    await router.push('/')
  } catch (err) {
    error.value = extractError(err, 'Unlock failed.')
    mode.value = 'passphrase'
  } finally {
    loading.value = false
  }
}

// ── PRF unlock (tap to unlock with passkey, no prfOutput in store yet) ────────
async function submitPrfUnlock(): Promise<void> {
  error.value = ''
  loading.value = true
  try {
    const { options } = await auth.webauthnAuthBegin(auth.username ?? undefined)
    const { prfOutput } = await getPasskey(options, true)
    if (!prfOutput) {
      error.value =
        'Your device does not support passkey unlock. Please use your passphrase instead.'
      return
    }
    const stored = await prf.retrievePrfPassphrase(prfOutput)
    if (!stored) {
      error.value = 'Could not decrypt with this passkey. Please use your passphrase.'
      prf.clearPrfPassphrase()
      hasPrfStored.value = false
      mode.value = 'passphrase'
      return
    }
    await auth.unlock(stored)
    await router.push('/')
  } catch (err) {
    error.value = extractError(err, 'Passkey unlock failed.')
  } finally {
    loading.value = false
  }
}

// ── PRF setup (save passphrase with passkey after successful passphrase unlock)
async function submitPrfSetup(): Promise<void> {
  error.value = ''
  loading.value = true
  try {
    const { options } = await auth.webauthnAuthBegin(auth.username ?? undefined)
    const { prfOutput } = await getPasskey(options, true)
    if (!prfOutput) {
      // This authenticator has no PRF: asking again on this device is pointless
      prf.dismissOffer()
      error.value =
        'This passkey cannot unlock encryption on this device. You will keep using your passphrase.'
      return
    }
    await prf.storePrfPassphrase(prfOutput, passphrase.value)
    await router.push('/')
  } catch (err) {
    error.value = extractError(err, 'Could not save passkey unlock. Make sure the app is served over HTTPS.')
  } finally {
    loading.value = false
  }
}

</script>

<template>
  <!-- ── PRF setup offer (after passphrase unlock) ── -->
  <div v-if="mode === 'prf-setup'" class="min-h-screen bg-base-200 flex items-center justify-center p-4">
    <div class="card bg-base-100 w-full max-w-sm shadow-xl">
      <div class="card-body">
        <h1 class="card-title text-xl justify-center mb-1">🔑 Unlock with passkey?</h1>
        <p class="text-center text-base-content/60 text-sm mb-4">
          Save your passphrase to this device so your passkey (Touch ID / Face ID) unlocks the app
          automatically — no passphrase to type next time.
        </p>

        <div v-if="error" class="alert alert-error text-sm py-2">{{ error }}</div>

        <button class="btn btn-primary mt-2" :disabled="loading" @click="submitPrfSetup">
          <span v-if="loading" class="loading loading-spinner loading-sm"></span>
          Save with passkey
        </button>
        <button type="button" class="btn btn-ghost btn-sm" @click="router.push('/')">
          Skip for now
        </button>
        <button type="button" class="btn btn-ghost btn-xs" @click="declinePrfSetup">
          Don't ask again on this device
        </button>
      </div>
    </div>
  </div>

  <!-- ── PRF unlock (tap passkey to decrypt) ── -->
  <div v-else-if="mode === 'prf'" class="min-h-screen bg-base-200 flex items-center justify-center p-4">
    <div class="card bg-base-100 w-full max-w-sm shadow-xl">
      <div class="card-body">
        <h1 class="card-title text-2xl justify-center mb-1">🔑 Unlock</h1>
        <p class="text-center text-base-content/60 text-sm mb-4">
          Welcome back, <strong>{{ auth.username }}</strong>. Use your passkey to unlock.
        </p>

        <div v-if="error" class="alert alert-error text-sm py-2">{{ error }}</div>

        <button class="btn btn-primary mt-2" :disabled="loading" @click="submitPrfUnlock">
          <span v-if="loading" class="loading loading-spinner loading-sm"></span>
          Unlock with passkey
        </button>

        <button
          type="button"
          class="btn btn-ghost btn-sm"
          @click="mode = 'passphrase'; error = ''"
        >
          Use passphrase instead
        </button>

        <button
          type="button"
          class="btn btn-ghost btn-sm"
          @click="auth.logout(); $router.push({ name: 'login' })"
        >
          Sign out
        </button>
      </div>
    </div>
  </div>

  <!-- ── Passphrase unlock ── -->
  <div v-else class="min-h-screen bg-base-200 flex items-center justify-center p-4">
    <div class="card bg-base-100 w-full max-w-sm shadow-xl">
      <div class="card-body">
        <h1 class="card-title text-2xl justify-center mb-1">🔓 Unlock</h1>
        <p class="text-center text-base-content/60 text-sm mb-4">
          Welcome back, <strong>{{ auth.username }}</strong>. Enter your passphrase
          to decrypt your data.
        </p>

        <form @submit.prevent="submitPassphrase" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label"><span class="label-text">Passphrase</span></div>
            <input
              v-model="passphrase"
              type="password"
              placeholder="••••••••"
              class="input input-bordered"
              autocomplete="current-password"
              required
              autofocus
            />
          </label>

          <div v-if="error" class="alert alert-error text-sm py-2">{{ error }}</div>

          <button type="submit" class="btn btn-primary mt-2" :disabled="loading">
            <span v-if="loading" class="loading loading-spinner loading-sm"></span>
            Unlock
          </button>

          <button
            v-if="hasPrfStored"
            type="button"
            class="btn btn-ghost btn-sm"
            @click="mode = 'prf'; error = ''"
          >
            Use passkey instead
          </button>

          <button
            type="button"
            class="btn btn-ghost btn-sm"
            @click="auth.logout(); $router.push({ name: 'login' })"
          >
            Sign out
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

