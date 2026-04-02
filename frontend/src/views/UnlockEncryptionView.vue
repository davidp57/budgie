<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePinStorage } from '@/composables/usePinStorage'
import { usePrfStorage } from '@/composables/usePrfStorage'
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
const pin = usePinStorage()
const prf = usePrfStorage()

// ── UI state ──────────────────────────────────────────────────────────────────
/**
 * 'passphrase' — standard passphrase entry
 * 'pin'        — PIN entry (localStorage passphrase stored)
 * 'pin-setup'  — offer PIN setup after successful passphrase unlock
 * 'prf'        — tap to unlock with passkey (PRF-wrapped passphrase stored)
 * 'prf-setup'  — offer passkey unlock setup after successful passphrase unlock
 */
type UnlockMode = 'passphrase' | 'pin' | 'pin-setup' | 'prf' | 'prf-setup'
const mode = ref<UnlockMode>('passphrase')

const passphrase = ref('')
const pinValue = ref('')
const newPin = ref('')
const newPinConfirm = ref('')
const error = ref('')
const loading = ref(false)

/** PIN requires crypto.subtle which is only available on HTTPS / localhost. */
const pinAvailable = typeof window !== 'undefined' && !!window.crypto?.subtle

const hasPinStored = ref(false)
const hasPrfStored = ref(false)
const pinRemainingAttempts = ref(5)

onMounted(async () => {
  if (!pinAvailable) return
  hasPinStored.value = await pin.hasStoredPassphrase()
  hasPrfStored.value = prf.hasPrfPassphrase()
  pinRemainingAttempts.value = pin.getRemainingAttempts()

  // Seamless PRF unlock: passkey was just used to log in and PRF output is in store
  if (hasPrfStored.value && auth.prfOutput) {
    await autoPrfUnlock(auth.prfOutput)
    return
  }
  if (hasPrfStored.value) {
    mode.value = 'prf'
  } else if (hasPinStored.value) {
    mode.value = 'pin'
  }
})

// ── Passphrase unlock ─────────────────────────────────────────────────────────
async function submitPassphrase(): Promise<void> {
  error.value = ''
  loading.value = true
  try {
    await auth.unlock(passphrase.value)
    // Offer passkey-based unlock first (stronger UX), then PIN, then done
    if (pinAvailable && !hasPrfStored.value && isWebAuthnSupported()) {
      mode.value = 'prf-setup'
    } else if (pinAvailable && !hasPinStored.value) {
      mode.value = 'pin-setup'
    } else {
      await router.push('/')
    }
  } catch (err) {
    error.value = extractError(err, 'Incorrect passphrase.')
  } finally {
    loading.value = false
  }
}

// ── PIN unlock ────────────────────────────────────────────────────────────────
async function submitPin(): Promise<void> {
  error.value = ''
  loading.value = true
  try {
    const stored = await pin.retrievePassphrase(pinValue.value)
    if (!stored) {
      pinRemainingAttempts.value = pin.getRemainingAttempts()
      if (pinRemainingAttempts.value === 0) {
        hasPinStored.value = false
        mode.value = 'passphrase'
        error.value = 'Too many wrong attempts. Please enter your passphrase.'
      } else {
        error.value = `Wrong PIN. ${pinRemainingAttempts.value} attempt${pinRemainingAttempts.value === 1 ? '' : 's'} remaining.`
      }
      return
    }
    await auth.unlock(stored)
    await router.push('/')
  } catch (err) {
    error.value = extractError(err, 'Unlock failed.')
  } finally {
    loading.value = false
  }
}

// ── PIN setup (after successful passphrase unlock) ────────────────────────────
async function submitPinSetup(): Promise<void> {
  if (newPin.value !== newPinConfirm.value) {
    error.value = 'PINs do not match.'
    return
  }
  error.value = ''
  loading.value = true
  try {
    await pin.storePassphrase(newPin.value, passphrase.value)
    await router.push('/')
  } catch (err) {
    // Surface the real error so the user knows the PIN was NOT saved
    error.value = extractError(err, 'Could not save PIN. Make sure the app is served over HTTPS.')
  } finally {
    loading.value = false
  }
}

async function skipPinSetup(): Promise<void> {
  await router.push('/')
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
      mode.value = hasPinStored.value ? 'pin' : 'passphrase'
      return
    }
    await auth.unlock(stored)
    await router.push('/')
  } catch (err) {
    error.value = extractError(err, 'Unlock failed.')
    mode.value = hasPinStored.value ? 'pin' : 'passphrase'
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
        'Your device does not support passkey unlock. Please use PIN or passphrase instead.'
      return
    }
    const stored = await prf.retrievePrfPassphrase(prfOutput)
    if (!stored) {
      error.value = 'Could not decrypt with this passkey. Please use your passphrase.'
      prf.clearPrfPassphrase()
      hasPrfStored.value = false
      mode.value = hasPinStored.value ? 'pin' : 'passphrase'
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
      error.value =
        'Your device does not support passkey unlock. Would you like to set up a PIN instead?'
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

async function skipPrfSetup(): Promise<void> {
  // Offer PIN as fallback if not yet configured
  if (pinAvailable && !hasPinStored.value) {
    error.value = ''
    mode.value = 'pin-setup'
  } else {
    await router.push('/')
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
          automatically — no PIN or passphrase to type next time.
        </p>

        <div v-if="error" class="alert alert-error text-sm py-2">{{ error }}</div>

        <button class="btn btn-primary mt-2" :disabled="loading" @click="submitPrfSetup">
          <span v-if="loading" class="loading loading-spinner loading-sm"></span>
          Save with passkey
        </button>
        <button type="button" class="btn btn-ghost btn-sm" @click="skipPrfSetup">
          Use PIN instead
        </button>
        <button type="button" class="btn btn-ghost btn-sm" @click="router.push('/')">
          Skip for now
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
          v-if="hasPinStored"
          type="button"
          class="btn btn-ghost btn-sm"
          @click="mode = 'pin'; error = ''"
        >
          Use PIN instead
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

  <!-- ── PIN setup offer ── -->
  <div v-if="mode === 'pin-setup'" class="min-h-screen bg-base-200 flex items-center justify-center p-4">
    <div class="card bg-base-100 w-full max-w-sm shadow-xl">
      <div class="card-body">
        <h1 class="card-title text-xl justify-center mb-1">🔢 Save with PIN?</h1>
        <p class="text-center text-base-content/60 text-sm mb-4">
          Protect your passphrase with a short PIN so you don't have to type it every time.
          The PIN never leaves this device.
        </p>

        <form @submit.prevent="submitPinSetup" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label"><span class="label-text">New PIN (4–6 digits)</span></div>
            <input
              v-model="newPin"
              type="password"
              inputmode="numeric"
              pattern="[0-9]{4,6}"
              placeholder="••••"
              class="input input-bordered text-center tracking-widest"
              minlength="4"
              maxlength="6"
              required
              autofocus
            />
          </label>
          <label class="form-control">
            <div class="label"><span class="label-text">Confirm PIN</span></div>
            <input
              v-model="newPinConfirm"
              type="password"
              inputmode="numeric"
              pattern="[0-9]{4,6}"
              placeholder="••••"
              class="input input-bordered text-center tracking-widest"
              minlength="4"
              maxlength="6"
              required
            />
          </label>

          <div v-if="error" class="alert alert-error text-sm py-2">{{ error }}</div>

          <button type="submit" class="btn btn-primary mt-2" :disabled="loading">
            <span v-if="loading" class="loading loading-spinner loading-sm"></span>
            Save PIN
          </button>
          <button type="button" class="btn btn-ghost btn-sm" @click="skipPinSetup">
            Skip for now
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- ── PIN unlock ── -->
  <div v-else-if="mode === 'pin'" class="min-h-screen bg-base-200 flex items-center justify-center p-4">
    <div class="card bg-base-100 w-full max-w-sm shadow-xl">
      <div class="card-body">
        <h1 class="card-title text-2xl justify-center mb-1">🔢 PIN</h1>
        <p class="text-center text-base-content/60 text-sm mb-4">
          Welcome back, <strong>{{ auth.username }}</strong>. Enter your PIN to unlock.
        </p>

        <form @submit.prevent="submitPin" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label"><span class="label-text">PIN</span></div>
            <input
              v-model="pinValue"
              type="password"
              inputmode="numeric"
              placeholder="••••"
              class="input input-bordered text-center tracking-widest text-xl"
              minlength="4"
              maxlength="6"
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
        </form>
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
            v-if="hasPinStored"
            type="button"
            class="btn btn-ghost btn-sm"
            @click="mode = 'pin'; error = ''"
          >
            Use PIN instead
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

