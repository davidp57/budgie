<script setup lang="ts">
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()

const alertClass: Record<string, string> = {
  info: 'alert-info',
  success: 'alert-success',
  warning: 'alert-warning',
  error: 'alert-error',
}
</script>

<template>
  <!-- Fixed bottom-end stack, above everything -->
  <div class="toast toast-end toast-bottom z-[9999]">
    <TransitionGroup name="toast">
      <div
        v-for="t in toast.toasts"
        :key="t.id"
        class="alert shadow-lg max-w-sm cursor-pointer"
        :class="alertClass[t.type]"
        @click="toast.remove(t.id)"
      >
        <span class="text-sm">{{ t.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(40px);
}
</style>
