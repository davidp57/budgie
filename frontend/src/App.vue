<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import ToastContainer from '@/components/ToastContainer.vue'
import AppNav from '@/components/AppNav.vue'
import client from '@/api/client'

const route = useRoute()
const showNav = computed(() => route.name !== 'login')
const appVersion = ref('')

onMounted(async () => {
  try {
    const { data } = await client.get<{ version: string }>('/api/health')
    appVersion.value = data.version
  } catch {
    // health endpoint not available — silently ignore
  }
})
</script>

<template>
  <div class="flex flex-col lg:flex-row h-dvh bg-base-200">
    <!-- Navigation: sidebar on desktop, bottom dock on mobile -->
    <AppNav v-if="showNav" />

    <!-- Main content area — scrollable -->
    <main class="flex-1 min-h-0 overflow-y-auto pb-16 lg:pb-0">
      <RouterView />
    </main>
  </div>

  <!-- App footer -->
  <footer
    v-if="showNav && appVersion"
    class="fixed bottom-16 lg:bottom-0 right-0 px-2 py-0.5 text-[10px] text-base-content/30 pointer-events-none select-none z-10"
  >
    Budgie v{{ appVersion }}
  </footer>

  <!-- Global toast notifications -->
  <ToastContainer />
</template>
