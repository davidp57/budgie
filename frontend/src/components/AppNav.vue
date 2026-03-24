<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

function logout(): void {
  auth.logout()
  router.push({ name: 'login' })
}

const links = [
  { path: '/', label: 'Tiroirs', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { path: '/budget', label: 'Budget', icon: 'M9 7h6m0 10v-3m-3 3v-6m-3 6v-1M3 17V7a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2z' },
  { path: '/transactions', label: 'Transactions', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
  { path: '/settings', label: 'Réglages', icons: ['M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z', 'M15 12a3 3 0 11-6 0 3 3 0 016 0z'] },
]
</script>

<template>
  <!-- Mobile: bottom dock -->
  <div class="dock dock-sm lg:hidden">
    <button
      v-for="link in links"
      :key="link.path"
      :class="{ 'dock-active': route.path === link.path }"
      @click="router.push(link.path)"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="size-[1.2em]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          v-if="link.icon"
          stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          :d="link.icon"
        />
        <path
          v-for="(d, i) in link.icons ?? []"
          :key="i"
          stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          :d="d"
        />
      </svg>
      <span class="dock-label">{{ link.label }}</span>
    </button>
  </div>

  <!-- Desktop: left sidebar -->
  <aside class="hidden lg:flex flex-col w-56 bg-base-100 border-r border-base-300 shrink-0">
    <div class="flex items-center gap-2 px-5 py-4">
      <span class="text-2xl">🐦</span>
      <span class="font-bold text-lg">Budgie</span>
    </div>

    <nav class="flex flex-col gap-1 px-3 flex-1">
      <button
        v-for="link in links"
        :key="link.path"
        class="btn btn-ghost justify-start gap-3 font-normal"
        :class="{ 'btn-active': route.path === link.path }"
        @click="router.push(link.path)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            v-if="link.icon"
            stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            :d="link.icon"
          />
          <path
            v-for="(d, i) in link.icons ?? []"
            :key="i"
            stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            :d="d"
          />
        </svg>
        {{ link.label }}
      </button>
    </nav>

    <!-- Logout button at bottom of sidebar -->
    <div class="px-3 pb-4">
      <button class="btn btn-ghost btn-sm justify-start gap-3 font-normal w-full text-base-content/50" @click="logout">
        <svg xmlns="http://www.w3.org/2000/svg" class="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
        Déconnexion
      </button>
    </div>
  </aside>
</template>
