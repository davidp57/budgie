/**
 * Theme composable — persists dark/light preference in localStorage and
 * applies the DaisyUI `data-theme` attribute to `<html>`.
 */
import { ref, watch } from 'vue'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'budgie-theme'

function getInitial(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark' || stored === 'light') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

const theme = ref<Theme>(getInitial())

function apply(t: Theme): void {
  document.documentElement.setAttribute('data-theme', t === 'dark' ? 'night' : 'emerald')
}

// Apply immediately on module load
apply(theme.value)

watch(theme, (t) => {
  apply(t)
  localStorage.setItem(STORAGE_KEY, t)
})

export function useTheme() {
  function toggle(): void {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  return { theme, toggle }
}
