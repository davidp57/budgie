<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import ToastContainer from '@/components/ToastContainer.vue'

const auth = useAuthStore()
const router = useRouter()
const { theme, toggle: toggleTheme } = useTheme()

function logout(): void {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <!-- DaisyUI drawer — sidebar always open on lg+, toggleable on mobile -->
  <div class="drawer lg:drawer-open">
    <input id="main-drawer" type="checkbox" class="drawer-toggle" />

    <!-- Page content -->
    <div class="drawer-content flex flex-col min-h-screen">
      <!-- Navbar (mobile only toggle + top bar) -->
      <div class="navbar bg-base-100 shadow-sm lg:hidden">
        <label for="main-drawer" class="btn btn-ghost drawer-button">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </label>
        <span class="text-lg font-bold ml-2">🐦 Budgie</span>
      </div>

      <!-- Main content area -->
      <main class="flex-1 p-4 lg:p-8">
        <RouterView />
      </main>
    </div>

    <!-- Sidebar -->
    <div class="drawer-side z-40">
      <label for="main-drawer" aria-label="close sidebar" class="drawer-overlay"></label>
      <aside class="bg-base-200 min-h-full w-64 flex flex-col">
        <!-- Logo -->
        <div class="p-4 border-b border-base-300 flex items-center justify-between">
          <div>
            <span class="text-xl font-bold">🐦 Budgie</span>
            <p v-if="auth.username" class="text-sm text-base-content/60 mt-1">{{ auth.username }}</p>
          </div>
          <!-- Theme toggle -->
          <button
            class="btn btn-ghost btn-sm btn-square"
            :title="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
            @click="toggleTheme"
          >
            <span v-if="theme === 'dark'">☀️</span>
            <span v-else>🌙</span>
          </button>
        </div>

        <!-- Navigation -->
        <ul class="menu p-2 flex-1">
          <li>
            <RouterLink to="/" active-class="active" exact-active-class="active">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Dashboard
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/transactions" active-class="active">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Transactions
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/budget" active-class="active">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Budget
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/import" active-class="active">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Import
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/settings" active-class="active">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Settings
            </RouterLink>
          </li>
        </ul>

        <!-- Logout -->
        <div class="p-2 border-t border-base-300">
          <button class="btn btn-ghost btn-sm w-full justify-start" @click="logout">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign out
          </button>
        </div>
      </aside>
    </div>
  </div>

  <!-- Global toast notifications -->
  <ToastContainer />
</template>
