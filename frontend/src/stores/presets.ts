/**
 * Quick-expense preset store.
 *
 * Persists user-customisable presets (emoji + amount + description)
 * to localStorage so they survive page reloads.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface QuickPreset {
  id: string
  emoji: string
  amount: number // centimes
  description: string
}

const DEFAULT_PRESETS: QuickPreset[] = [
  { id: 'default-1', emoji: '🍞', amount: 200, description: 'Pain' },
  { id: 'default-2', emoji: '☕', amount: 400, description: 'Café' },
  { id: 'default-3', emoji: '🥖', amount: 500, description: 'Boulangerie' },
  { id: 'default-4', emoji: '🍕', amount: 1200, description: 'Restaurant' },
  { id: 'default-5', emoji: '🛒', amount: 3000, description: 'Courses' },
  { id: 'default-6', emoji: '⛽', amount: 5000, description: 'Essence' },
]

const STORAGE_KEY = 'budgie-quick-presets'

function loadFromStorage(): QuickPreset[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw) as QuickPreset[]
  } catch {
    /* ignore corrupted data */
  }
  return DEFAULT_PRESETS.map((p) => ({ ...p }))
}

export const usePresetsStore = defineStore('presets', () => {
  const presets = ref<QuickPreset[]>(loadFromStorage())

  function persist(): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(presets.value))
  }

  function replaceAll(newPresets: QuickPreset[]): void {
    presets.value = newPresets
    persist()
  }

  function resetToDefaults(): void {
    presets.value = DEFAULT_PRESETS.map((p) => ({ ...p }))
    persist()
  }

  return { presets, replaceAll, resetToDefaults }
})
