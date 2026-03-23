<script setup lang="ts">
import { RouterView } from 'vue-router'
import ToastContainer from '@/components/ToastContainer.vue'
import BottomNav from '@/components/BottomNav.vue'
</script>

<template>
  <div class="flex flex-col h-dvh bg-base-200">
    <!-- Main content area — scrollable -->
    <main class="flex-1 overflow-y-auto">
      <RouterView />
    </main>

    <!-- Bottom navigation bar -->
    <BottomNav />
  </div>

  <!-- Global toast notifications -->
  <ToastContainer />
</template>
