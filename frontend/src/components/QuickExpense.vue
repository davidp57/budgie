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

import { computed, nextTick, onMounted, ref } from 'vue'
import type { EnvelopeLine } from '@/api/types'
import { formatAmount } from '@/api/types'
import { createTransaction } from '@/api/transactions'
import { useToastStore } from '@/stores/toast'
import { usePresetsStore, type QuickPreset } from '@/stores/presets'
import { useNearbyPlaces } from '@/composables/useNearbyPlaces'

const props = defineProps<{
  drawer: EnvelopeLine
  accountId: number
}>()

const emit = defineEmits<{
  close: []
}>()

const toast = useToastStore()
const presetsStore = usePresetsStore()
const nearby = useNearbyPlaces()
const showLocation = ref(false)
const desktopAmountInput = ref<HTMLInputElement | null>(null)

// Responsive: detect desktop
const isDesktop = ref(window.matchMedia('(min-width: 1024px)').matches)

// Auto-focus the desktop amount input
onMounted(() => {
  nextTick(() => desktopAmountInput.value?.focus())
})

// Amount as string (user types digits + comma)
const amountStr = ref('')
const description = ref('')
const showDescription = ref(false)
const showDate = ref(false)
const isPlanned = ref(false)
const customDate = ref(new Date().toISOString().slice(0, 10))
const submitting = ref(false)

// Parse amount string to centimes (strict validation)
// Accept both comma and dot as decimal separator
const AMOUNT_RE = /^\d+([.,]\d{0,2})?$/

const amountError = computed(() => {
  if (!amountStr.value) return ''
  if (!AMOUNT_RE.test(amountStr.value)) return 'Montant invalide'
  return ''
})

const amountCentimes = computed(() => {
  if (!amountStr.value || amountError.value) return 0
  const normalized = amountStr.value.replace('.', ',')
  const parts = normalized.split(',')
  const euros = parseInt(parts[0] || '0', 10)
  let cents = 0
  if (parts[1]) {
    const rawCents = parts[1].slice(0, 2)
    cents = parseInt(rawCents.padEnd(2, '0'), 10)
  }
  return euros * 100 + cents
})

const hasAmount = computed(() => amountCentimes.value > 0)

// Display formatted amount (French locale: space thousands separator)
const displayAmount = computed(() => {
  if (!amountStr.value) return ''
  const parts = amountStr.value.split(',')
  const intPart = parts[0] || '0'
  const formatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '\u202F')
  return parts.length > 1 ? `${formatted},${parts[1]}` : formatted
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

// Preset tap — fills amount AND description
function onPreset(preset: QuickPreset): void {
  const euros = Math.floor(preset.amount / 100)
  const cents = preset.amount % 100
  amountStr.value = cents > 0 ? `${euros},${String(cents).padEnd(2, '0')}` : `${euros}`
  if (preset.description) {
    description.value = preset.description
    showDescription.value = true
  }
}

// Format preset amount for button label
function formatPresetAmount(centimes: number): string {
  const euros = centimes / 100
  return euros % 1 === 0
    ? `${euros}€`
    : `${euros.toFixed(2).replace('.', ',')}€`
}

// ── Nearby places ────────────────────────────────────────────────
function toggleLocation(): void {
  showLocation.value = !showLocation.value
  if (showLocation.value && !nearby.hasPlaces.value && !nearby.loading.value) {
    nearby.detect()
  }
}

function selectPlace(name: string): void {
  description.value = name
  showDescription.value = true
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
      account_id: props.accountId,
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

// ── Preset management dialog ─────────────────────────────────────
const presetDialogRef = ref<HTMLDialogElement | null>(null)
const editingPresets = ref<Array<{
  id: string
  emoji: string
  amountStr: string
  description: string
}>>([])

function openPresetManager(): void {
  editingPresets.value = presetsStore.presets.map((p) => ({
    id: p.id,
    emoji: p.emoji,
    amountStr: formatPresetAmount(p.amount).replace('€', ''),
    description: p.description,
  }))
  presetDialogRef.value?.showModal()
}

function addEditingPreset(): void {
  editingPresets.value.push({
    id: crypto.randomUUID(),
    emoji: '🏷️',
    amountStr: '',
    description: '',
  })
}

function removeEditingPreset(id: string): void {
  editingPresets.value = editingPresets.value.filter((p) => p.id !== id)
}

function parseAmountStr(str: string): number {
  const cleaned = str.replace(',', '.').replace(/[^\d.]/g, '')
  return Math.round((parseFloat(cleaned) || 0) * 100)
}

function savePresets(): void {
  const parsed: QuickPreset[] = editingPresets.value
    .filter((p) => p.amountStr.trim())
    .map((p) => ({
      id: p.id,
      emoji: p.emoji || '🏷️',
      amount: parseAmountStr(p.amountStr),
      description: p.description,
    }))
  presetsStore.replaceAll(parsed)
  presetDialogRef.value?.close()
}

function resetPresetsToDefaults(): void {
  presetsStore.resetToDefaults()
  editingPresets.value = presetsStore.presets.map((p) => ({
    id: p.id,
    emoji: p.emoji,
    amountStr: formatPresetAmount(p.amount).replace('€', ''),
    description: p.description,
  }))
}

const numpadKeys = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
  [',', '0', '⌫'],
]
</script>

<template>
  <!-- Backdrop -->
  <div
    class="fixed inset-0 z-50 flex flex-col justify-end lg:items-center lg:justify-center"
    @keydown.escape="emit('close')"
  >
    <div class="absolute inset-0 bg-black/40" @click="emit('close')" />

    <!-- Bottom sheet (mobile) / Centered modal (desktop) -->
    <div class="relative bg-base-100 rounded-t-3xl lg:rounded-2xl shadow-2xl max-h-[92dvh] lg:max-h-[85vh] lg:w-full lg:max-w-md flex flex-col animate-slide-up lg:animate-none">
      <!-- Drag handle (mobile only) -->
      <div class="flex justify-center pt-3 pb-1 lg:hidden">
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
            <!-- Mobile: read-only display -->
            <template v-if="!isDesktop">
              <span
                v-if="!displayAmount"
                class="text-[48px] font-extrabold text-base-content/15 select-none"
              >0</span>
              <span v-else class="text-[48px] font-extrabold tabular-nums tracking-tight">{{ displayAmount }}</span>
              <span class="blink-cursor text-[48px] font-thin text-primary/60 select-none">|</span>
            </template>
            <!-- Desktop: editable input styled as the display -->
            <input
              v-else
              ref="desktopAmountInput"
              v-model="amountStr"
              type="text"
              inputmode="decimal"
              class="bg-transparent border-none outline-none text-center
                     text-[48px] font-extrabold tabular-nums tracking-tight
                     w-48 caret-primary placeholder:text-base-content/15"
              :class="amountError ? 'text-error' : ''"
              placeholder="0"
              @keydown.enter="submit"
              @keydown.escape="emit('close')"
            />
            <span class="text-2xl text-base-content/25 font-light ml-1">€</span>
          </div>
        </div>

        <!-- Presets -->
        <div class="flex gap-2 overflow-x-auto pb-3 -mx-1 px-1 scrollbar-none">
          <button
            v-for="preset in presetsStore.presets"
            :key="preset.id"
            class="btn btn-sm btn-outline btn-primary whitespace-nowrap flex-shrink-0"
            @click="onPreset(preset)"
          >{{ preset.emoji }} {{ formatPresetAmount(preset.amount) }}</button>
          <button
            class="btn btn-sm btn-ghost btn-circle flex-shrink-0 text-base-content/40"
            title="Configurer les raccourcis"
            @click="openPresetManager"
          >⚙️</button>
        </div>

        <!-- Optional field chips -->
        <div class="flex gap-2 py-2 flex-wrap">
          <button
            class="btn btn-xs"
            :class="showDescription ? 'btn-primary' : 'btn-ghost'"
            @click="showDescription = !showDescription"
          >✏️ Description</button>
          <button
            class="btn btn-xs"
            :class="showLocation ? 'btn-primary' : 'btn-ghost'"
            @click="toggleLocation"
          >
            <span v-if="nearby.loading.value" class="loading loading-spinner loading-xs" />
            <template v-else>📍 Lieu</template>
          </button>
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

        <!-- Nearby places (conditional) -->
        <div v-if="showLocation" class="mt-1 mb-1">
          <div v-if="nearby.loading.value" class="text-center py-2">
            <span class="loading loading-dots loading-sm text-primary" />
            <p class="text-xs text-base-content/50 mt-1">Recherche des commerces…</p>
          </div>
          <div v-else-if="nearby.error.value" class="text-xs text-error py-1">
            {{ nearby.error.value }}
          </div>
          <div v-else-if="nearby.hasPlaces.value" class="flex gap-2 overflow-x-auto pb-2 scrollbar-none">
            <button
              v-for="place in nearby.places.value"
              :key="place.id"
              class="btn btn-xs btn-outline whitespace-nowrap flex-shrink-0"
              :class="description === place.name ? 'btn-active' : ''"
              @click="selectPlace(place.name)"
            >
              {{ place.emoji }} {{ place.name }}
              <span class="text-[10px] opacity-50 ml-1">{{ nearby.formatDistance(place.distance) }}</span>
            </button>
          </div>
          <div v-else class="text-xs text-base-content/50 py-1">
            Aucun commerce trouvé à proximité
          </div>
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

        <!-- Custom numpad (mobile only) -->
        <div class="grid grid-cols-3 gap-2 mt-4 lg:hidden">
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
          :class="hasAmount && !amountError
            ? 'bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 shadow-lg'
            : 'btn-disabled bg-base-300 text-base-content/30'"
          :disabled="!hasAmount || !!amountError || submitting"
          @click="submit"
        >
          <span v-if="submitting" class="loading loading-spinner loading-sm" />
          <template v-else-if="amountError">
            {{ amountError }}
          </template>
          <template v-else-if="hasAmount">
            Dépenser {{ formatAmount(amountCentimes) }}
          </template>
          <template v-else>
            Entrer un montant
          </template>
        </button>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════ -->
    <!-- Preset Management Dialog                                   -->
    <!-- ═══════════════════════════════════════════════════════════ -->
    <dialog ref="presetDialogRef" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box">
        <h3 class="text-lg font-bold mb-4">⚙️ Raccourcis rapides</h3>

        <div class="space-y-2">
          <div
            v-for="p in editingPresets"
            :key="p.id"
            class="flex items-center gap-1"
          >
            <input
              v-model="p.emoji"
              class="input input-bordered input-sm w-14 text-center text-lg p-0"
              maxlength="2"
            />
            <input
              v-model="p.amountStr"
              class="input input-bordered input-sm w-20 text-right"
              placeholder="€"
              inputmode="decimal"
            />
            <input
              v-model="p.description"
              class="input input-bordered input-sm flex-1"
              placeholder="Description"
            />
            <button
              class="btn btn-ghost btn-sm btn-circle text-error"
              @click="removeEditingPreset(p.id)"
            >✕</button>
          </div>
        </div>

        <button
          class="btn btn-outline btn-sm btn-block mt-3"
          @click="addEditingPreset"
        >+ Ajouter</button>

        <div class="modal-action">
          <button class="btn btn-ghost btn-sm" @click="resetPresetsToDefaults">
            Par défaut
          </button>
          <button class="btn btn-primary btn-sm" @click="savePresets">
            OK
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>
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
