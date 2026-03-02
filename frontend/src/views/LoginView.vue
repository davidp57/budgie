<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit(): Promise<void> {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    await router.push('/')
  } catch {
    error.value = 'Invalid username or password.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-base-200 flex items-center justify-center">
    <div class="card bg-base-100 w-full max-w-sm shadow-xl">
      <div class="card-body">
        <h1 class="card-title text-2xl justify-center mb-2">🐦 Budgie</h1>
        <p class="text-center text-base-content/60 mb-4">Sign in to your account</p>

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
            <div class="label"><span class="label-text">Password</span></div>
            <input
              v-model="password"
              type="password"
              placeholder="••••••••"
              class="input input-bordered"
              autocomplete="current-password"
              required
            />
          </label>

          <div v-if="error" class="alert alert-error text-sm py-2">{{ error }}</div>

          <button type="submit" class="btn btn-primary mt-2" :disabled="loading">
            <span v-if="loading" class="loading loading-spinner loading-sm"></span>
            Sign in
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
