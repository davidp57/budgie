<script setup lang="ts">
import axios from 'axios'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { register as apiRegister } from '@/api/auth'

function extractError(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((d: { msg?: string }) => d.msg ?? '').join(' ')
    }
  }
  return fallback
}

const auth = useAuthStore()
const router = useRouter()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const passwordConfirm = ref('')
const error = ref('')
const loading = ref(false)

function switchMode(m: 'login' | 'register'): void {
  mode.value = m
  error.value = ''
  password.value = ''
  passwordConfirm.value = ''
}

async function submit(): Promise<void> {
  error.value = ''
  if (mode.value === 'register') {
    if (password.value !== passwordConfirm.value) {
      error.value = 'Passwords do not match.'
      return
    }
    loading.value = true
    try {
      await apiRegister(username.value, password.value)
      // auto-login after register
      await auth.login(username.value, password.value)
      await router.push('/')
    } catch (err) {
      error.value = extractError(err, 'Registration failed. Username may already be taken.')
    } finally {
      loading.value = false
    }
  } else {
    loading.value = true
    try {
      await auth.login(username.value, password.value)
      await router.push('/')
    } catch (err) {
      error.value = extractError(err, 'Invalid username or password.')
    } finally {
      loading.value = false
    }
  }
}
</script>

<template>
  <div class="min-h-screen bg-base-200 flex items-center justify-center">
    <div class="card bg-base-100 w-full max-w-sm shadow-xl">
      <div class="card-body">
        <h1 class="card-title text-2xl justify-center mb-4">🐦 Budgie</h1>

        <!-- Mode tabs -->
        <div role="tablist" class="tabs tabs-bordered mb-4">
          <button
            role="tab"
            class="tab"
            :class="{ 'tab-active': mode === 'login' }"
            @click="switchMode('login')"
          >
            Sign in
          </button>
          <button
            role="tab"
            class="tab"
            :class="{ 'tab-active': mode === 'register' }"
            @click="switchMode('register')"
          >
            Create account
          </button>
        </div>

        <form @submit.prevent="submit" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label"><span class="label-text">Username</span></div>
            <input
              v-model="username"
              type="text"
              placeholder="alice"
              class="input input-bordered"
              autocomplete="username"
              required
            />
          </label>

          <label class="form-control">
            <div class="label">
              <span class="label-text">Password</span>
              <span v-if="mode === 'register'" class="label-text-alt text-base-content/50">min. 8 characters</span>
            </div>
            <input
              v-model="password"
              type="password"
              placeholder="••••••••"
              class="input input-bordered"
              :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
              :minlength="mode === 'register' ? 8 : undefined"
              required
            />
          </label>

          <label v-if="mode === 'register'" class="form-control">
            <div class="label"><span class="label-text">Confirm password</span></div>
            <input
              v-model="passwordConfirm"
              type="password"
              placeholder="••••••••"
              class="input input-bordered"
              autocomplete="new-password"
              required
            />
          </label>

          <div v-if="error" class="alert alert-error text-sm py-2">{{ error }}</div>

          <button type="submit" class="btn btn-primary mt-2" :disabled="loading">
            <span v-if="loading" class="loading loading-spinner loading-sm"></span>
            {{ mode === 'login' ? 'Sign in' : 'Create account' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
