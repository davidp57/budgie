<script setup lang="ts">
/**
 * QuickExpense — Bottom sheet for rapid transaction entry.
 *
 * Design spec (from validated mockup):
 * - Slides up from bottom, drag handle
 * - Header: emoji + drawer name + remaining balance + ✕ close
 * - Big amount display (48px bold), blinking cursor, grayed €
 * - Preset buttons (horizontal scroll, configurable per drawer)
 * - Optional chip toggles: ✏️ Description, 📅 Date, 🔮 Planned
 * - Custom numpad 3×4 (1-9, comma, 0, backspace)
 * - Confirm: gray "Entrer un montant" → green "Dépenser X €"
 * - Toast confirmation, non-blocking, auto-dismiss
 */

import { computed, ref } from 'vue'
import type { EnvelopeLine } from '@/api/types'
import { formatAmount } from '@/api/types'
import { createTransaction } from '@/api/transactions'
import { useToastStore } from '@/stores/toast'

const props = defineProps<{
  drawer: EnvelopeLine
}>()

const emit = defineEmits<{
  close: []
}>()

const toast = useToastStore()

// Amount as string (user types digits + comma)
const amountStr = ref('')
const description = ref('')
const showDescription = ref(false)
const showDate = ref(false)
const isPlanned = ref(false)
const customDate = ref(new Date().toISOString().slice(0, 10))
const submitting = ref(false)

// Parse amount string to centimes
const amountCentimes = computed(() => {
  if (!amountStr.value) return 0
  const parts = amountStr.value.split(',')
  const euros = parseInt(parts[0] || '0', 10)
  let cents = 0
  if (parts[1]) {
    const rawCents = parts[1].slice(0, 2) // max 2 decimal places
    cents = parseInt(rawCents.padEnd(2, '0'), 10)
  }
  return euros * 100 + cents
})

const hasAmount = computed(() => amountCentimes.value > 0)

// Display formatted amount
const displayAmount = computed(() => {
  if (!amountStr.value) return ''
  return amountStr.value.replace(',', ',')
})

// Numpad key handler
function onKey(key: string): void {
  if (key === '⌫') {
    amountStr.value = amountStr.value.slice(0, -1)
    return
  }
  if (key === ',') {
    if (amountStr.value.includes(',')) return // already has comma
    if (!amountStr.value) amountStr.value = '0'
    amountStr.value += ','
    return
  }
  // Digit
  const parts = amountStr.value.split(',')
  if (parts[1] !== undefined && parts[1].length >= 2) return // max 2 decimals
  if (parts[0] === '0' && !amountStr.value.includes(',')) {
    amountStr.value = key // replace leading zero
    return
  }
  amountStr.value += key
}

// Preset tap
function onPreset(centimes: number): void {
  const euros = Math.floor(centimes / 100)
  const cents = centimes % 100
  amountStr.value = cents > 0 ? `${euros},${String(cents).padEnd(2, '0')}` : `${euros}`
}

// Submit transaction
async function submit(): Promise<void> {
  if (!hasAmount.value || submitting.value) return
  submitting.value = true

  try {
    // Use first category of the drawer
    const categoryId = props.drawer.categories[0]?.id
    if (!categoryId) {
      toast.error('⚠️ Ce tiroir n\u2019a aucune catégorie — ajoute-en une dans les réglages')
      submitting.value = false
      return
    }

    await createTransaction({
      account_id: 1, // Default account for MVP
      date: showDate.value ? customDate.value : new Date().toISOString().slice(0, 10),
      amount: -amountCentimes.value, // Expense = negative
      category_id: categoryId,
      memo: showDescription.value && description.value ? description.value : undefined,
      status: isPlanned.value ? 'planned' : 'real',
    })

    const remaining = props.drawer.available - amountCentimes.value
    toast.success(
      `✅ ${formatAmount(amountCentimes.value)} → ${props.drawer.envelope_name} · reste ${formatAmount(remaining)}`,
    )
    emit('close')
  } catch {
    toast.error('Erreur lors de la saisie')
  } finally {
    submitting.value = false
  }
}

// Default presets (can be per-drawer later)
const presets = [
  { label: '🍞 2€', centimes: 200 },
  { label: '☕ 4€', centimes: 400 },
  { label: '🥖 5€', centimes: 500 },
  { label: '🍕 12€', centimes: 1200 },
  { label: '🛒 30€', centimes: 3000 },
  { label: '🛒 50€', centimes: 5000 },
]

const numpadKeys = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
  [',', '0', '⌫'],
]
</script>

<template>
  <!-- Backdrop -->
  <div class="fixed inset-0 z-50 flex flex-col justify-end">
    <div class="absolute inset-0 bg-black/40" @click="emit('close')" />

    <!-- Bottom sheet -->
    <div class="relative bg-base-100 rounded-t-3xl shadow-2xl max-h-[92dvh] flex flex-col animate-slide-up">
      <!-- Drag handle -->
      <div class="flex justify-center pt-3 pb-1">
        <div class="w-10 h-1 rounded-full bg-base-300" />
      </div>

      <!-- Header -->
      <div class="flex items-center justify-between px-5 pb-3">
        <div class="flex items-center gap-2 min-w-0">
          <span class="text-2xl">{{ props.drawer.emoji || '📦' }}</span>
          <div class="min-w-0">
            <p class="font-semibold truncate">{{ drawer.envelope_name }}</p>
            <p class="text-xs text-base-content/50">
              Reste {{ formatAmount(drawer.available) }}
            </p>
          </div>
        </div>
        <button class="btn btn-ghost btn-sm btn-circle" @click="emit('close')">✕</button>
      </div>

      <!-- Scrollable content -->
      <div class="flex-1 overflow-y-auto px-5 pb-4">
        <!-- Amount display -->
        <div class="text-center py-6">
          <div class="flex items-baseline justify-center gap-1 min-h-[64px]">
            <span
              v-if="!displayAmount"
              class="text-[48px] font-extrabold text-base-content/15 select-none"
            >0</span>
            <span v-else class="text-[48px] font-extrabold tabular-nums tracking-tight">{{ displayAmount }}</span>
            <span class="blink-cursor text-[48px] font-thin text-primary/60 select-none">|</span>
            <span class="text-2xl text-base-content/25 font-light ml-1">€</span>
          </div>
        </div>

        <!-- Presets -->
        <div class="flex gap-2 overflow-x-auto pb-3 -mx-1 px-1 scrollbar-none">
          <button
            v-for="preset in presets"
            :key="preset.centimes"
            class="btn btn-sm btn-outline btn-primary whitespace-nowrap flex-shrink-0"
            @click="onPreset(preset.centimes)"
          >{{ preset.label }}</button>
        </div>

        <!-- Optional field chips -->
        <div class="flex gap-2 py-2">
          <button
            class="btn btn-xs"
            :class="showDescription ? 'btn-primary' : 'btn-ghost'"
            @click="showDescription = !showDescription"
          >✏️ Description</button>
          <button
            class="btn btn-xs"
            :class="showDate ? 'btn-primary' : 'btn-ghost'"
            @click="showDate = !showDate"
          >📅 Date</button>
          <button
            class="btn btn-xs"
            :class="isPlanned ? 'btn-primary' : 'btn-ghost'"
            @click="isPlanned = !isPlanned"
          >🔮 Prévue</button>
        </div>

        <!-- Description input (conditional) -->
        <input
          v-if="showDescription"
          v-model="description"
          type="text"
          placeholder="Description..."
          class="input input-bordered input-sm w-full mt-1"
        />

        <!-- Date picker (conditional) -->
        <input
          v-if="showDate"
          v-model="customDate"
          type="date"
          class="input input-bordered input-sm w-full mt-1"
        />

        <!-- Custom numpad -->
        <div class="grid grid-cols-3 gap-2 mt-4">
          <template v-for="row in numpadKeys" :key="row.join()">
            <button
              v-for="key in row"
              :key="key"
              class="btn btn-lg text-xl font-medium"
              :class="key === '⌫' ? 'btn-ghost' : 'btn-ghost bg-base-200'"
              @click="onKey(key)"
            >{{ key }}</button>
          </template>
        </div>

        <!-- Confirm button -->
        <button
          class="btn btn-lg w-full mt-4 text-white font-semibold"
          :class="hasAmount
            ? 'bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 shadow-lg'
            : 'btn-disabled bg-base-300 text-base-content/30'"
          :disabled="!hasAmount || submitting"
          @click="submit"
        >
          <span v-if="submitting" class="loading loading-spinner loading-sm" />
          <template v-else-if="hasAmount">
            Dépenser {{ formatAmount(amountCentimes) }}
          </template>
          <template v-else>
            Entrer un montant
          </template>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-slide-up {
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(100%);
  }
  to {
    transform: translateY(0);
  }
}

.scrollbar-none {
  scrollbar-width: none;
}

.scrollbar-none::-webkit-scrollbar {
  display: none;
}

/* Blinking cursor */
.blink-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
