<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import ToastContainer from '@/components/ToastContainer.vue'
import AppNav from '@/components/AppNav.vue'

const route = useRoute()
const showNav = computed(() => route.name !== 'login')
</script>

<template>
  <div class="flex flex-col lg:flex-row h-dvh bg-base-200">
    <!-- Navigation: sidebar on desktop, bottom dock on mobile -->
    <AppNav v-if="showNav" />

    <!-- Main content area — scrollable -->
    <main class="flex-1 overflow-y-auto pb-16 lg:pb-0">
      <RouterView />
    </main>
  </div>

  <!-- Global toast notifications -->
  <ToastContainer />
</template>
