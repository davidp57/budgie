<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePinStorage } from '@/composables/usePinStorage'

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

// ── UI state ──────────────────────────────────────────────────────────────────
/**
 * 'passphrase' — standard passphrase entry
 * 'pin'        — PIN entry (localStorage passphrase stored)
 * 'pin-setup'  — offer PIN setup after successful passphrase unlock
 */
type UnlockMode = 'passphrase' | 'pin' | 'pin-setup'
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
const pinRemainingAttempts = ref(5)

onMounted(async () => {
  if (!pinAvailable) return
  hasPinStored.value = await pin.hasStoredPassphrase()
  pinRemainingAttempts.value = pin.getRemainingAttempts()
  if (hasPinStored.value) mode.value = 'pin'
})

// ── Passphrase unlock ─────────────────────────────────────────────────────────
async function submitPassphrase(): Promise<void> {
  error.value = ''
  loading.value = true
  try {
    await auth.unlock(passphrase.value)
    // Offer PIN setup if crypto is available and PIN not yet configured
    if (pinAvailable && !hasPinStored.value) {
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
</script>

<template>
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

