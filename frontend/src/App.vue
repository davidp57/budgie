<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import ToastContainer from '@/components/ToastContainer.vue'
import BottomNav from '@/components/BottomNav.vue'

const route = useRoute()
const showNav = computed(() => route.name !== 'login')
</script>

<template>
  <div class="flex flex-col h-dvh bg-base-200">
    <!-- Main content area — scrollable -->
    <main class="flex-1 overflow-y-auto">
      <RouterView />
    </main>

    <!-- Bottom navigation bar (hidden on login page) -->
    <BottomNav v-if="showNav" />
  </div>

  <!-- Global toast notifications -->
  <ToastContainer />
</template>
