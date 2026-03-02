/**
 * Toast notification store.
 *
 * Provides a tiny queue of transient alert messages displayed by
 * ToastContainer.vue.  Each toast auto-dismisses after `duration` ms.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastType = 'info' | 'success' | 'warning' | 'error'

export interface Toast {
  id: number
  message: string
  type: ToastType
}

let nextId = 1

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])

  function add(message: string, type: ToastType = 'info', duration = 4000): void {
    const id = nextId++
    toasts.value.push({ id, message, type })
    setTimeout(() => remove(id), duration)
  }

  function remove(id: number): void {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  /** Convenience shortcuts */
  const success = (message: string) => add(message, 'success')
  const error = (message: string) => add(message, 'error', 6000)
  const warning = (message: string) => add(message, 'warning')
  const info = (message: string) => add(message, 'info')

  return { toasts, add, remove, success, error, warning, info }
})
