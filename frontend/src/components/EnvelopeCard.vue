<script setup lang="ts">
/**
 * EnvelopeCard — displays one budget envelope row with inline editing.
 *
 * Props:
 *   envelope    — the EnvelopeLine from the backend
 *   editedValue — centimes override (undefined = use envelope.budgeted)
 *   selected    — highlight this row (envelope is active filter)
 *
 * Emits:
 *   edit(centimes)          — user finished editing the budgeted amount
 *   select(envelopeId)      — row clicked (for transaction filtering)
 *   add-transaction(id)     — "Add transaction" action clicked
 *   edit-envelope(id)       — "Edit envelope" action clicked
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { formatAmount, type EnvelopeLine } from '@/api/types'

const props = defineProps<{
  envelope: EnvelopeLine
  editedValue?: number
  selected?: boolean
}>()

const emit = defineEmits<{
  edit: [value: number]
  select: [envelopeId: number]
  'add-transaction': [envelopeId: number]
  'edit-envelope': [envelopeId: number]
}>()

const editing = ref(false)
const menuOpen = ref(false)

function handleOutsideClick(): void {
  menuOpen.value = false
}

const inputValue = ref(displayEuros(props.editedValue ?? props.envelope.budgeted))

watch(
  () => props.editedValue ?? props.envelope.budgeted,
  (v) => {
    if (!editing.value) inputValue.value = displayEuros(v)
  },
)

function displayEuros(centimes: number): string {
  return (centimes / 100).toFixed(2)
}

function startEdit(): void {
  editing.value = true
  inputValue.value = displayEuros(props.editedValue ?? props.envelope.budgeted)
}

function commitEdit(): void {
  editing.value = false
  const euros = parseFloat(String(inputValue.value).replace(',', '.')) || 0
  emit('edit', Math.round(euros * 100))
}

function toggleMenu(e: Event): void {
  e.stopPropagation()
  if (!menuOpen.value) {
    menuOpen.value = true
    // Close on next outside click
    setTimeout(() => document.addEventListener('click', handleOutsideClick, { once: true }), 0)
  } else {
    menuOpen.value = false
  }
}

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
})

function onAddTransaction(e: Event): void {
  e.stopPropagation()
  menuOpen.value = false
  emit('add-transaction', props.envelope.envelope_id)
}

function onEditEnvelope(e: Event): void {
  e.stopPropagation()
  menuOpen.value = false
  emit('edit-envelope', props.envelope.envelope_id)
}

const availableClass = computed(() =>
  props.envelope.available < 0 ? 'text-error font-semibold' : 'text-success',
)

const categoryLabel = computed(() =>
  props.envelope.categories.map((c) => c.name).join(' · '),
)

// ── Envelope fill visual ──────────────────────────────────────────
const fillRatio = computed<number>(() => {
  const budgeted = props.editedValue ?? props.envelope.budgeted
  if (budgeted <= 0) return props.envelope.available > 0 ? 1 : 0
  return Math.max(0, Math.min(1, props.envelope.available / budgeted))
})

const fillColor = computed<string>(() =>
  props.envelope.available < 0 ? '#f87272' : '#85BB65',
)

const clipId = computed(() => `env-clip-${props.envelope.envelope_id}`)
const fillY = computed(() => 44 - 42 * fillRatio.value)
</script>

<template>
  <div
    class="grid grid-cols-[1fr_120px_120px_120px] gap-2 items-center py-2 border-b border-base-300/50 last:border-0 cursor-pointer rounded transition-colors"
    :class="selected ? 'bg-primary/10' : 'hover:bg-base-200/50'"
    @click="emit('select', envelope.envelope_id)"
  >
    <!-- Left: SVG + name + action button -->
    <div class="min-w-0 flex items-center gap-3">
      <!-- Envelope SVG — 1.5× size (87×60) -->
      <svg
        viewBox="0 0 64 44"
        width="87"
        height="60"
        class="shrink-0"
        aria-hidden="true"
      >
        <defs>
          <clipPath :id="clipId">
            <rect x="1" y="1" width="62" height="42" rx="2" />
          </clipPath>
        </defs>
        <!-- Fill -->
        <rect
          x="1"
          :y="fillY"
          width="62"
          :height="42 * fillRatio"
          :fill="fillColor"
          :clip-path="`url(#${clipId})`"
          opacity="0.85"
        />
        <!-- Body -->
        <rect x="1" y="1" width="62" height="42" rx="2"
          fill="none" stroke="currentColor" stroke-width="1.5"
          class="text-base-content/70" />
        <!-- Top flap -->
        <path d="M 1 1 L 63 1 L 32 23 Z"
          fill="none" stroke="currentColor" stroke-width="1"
          class="text-base-content/50" />
        <!-- Fold lines -->
        <line x1="1" y1="43" x2="32" y2="23"
          stroke="currentColor" stroke-width="0.8" class="text-base-content/30" />
        <line x1="63" y1="43" x2="32" y2="23"
          stroke="currentColor" stroke-width="0.8" class="text-base-content/30" />
        <!-- Stamp -->
        <rect x="50" y="5" width="10" height="13" rx="1"
          fill="none" stroke="currentColor" stroke-width="1"
          class="text-base-content/35" />
        <rect x="52" y="7" width="6" height="9" rx="0.5"
          fill="currentColor" opacity="0.08" />
        <!-- Address lines -->
        <line x1="7" y1="30" x2="41" y2="30"
          stroke="currentColor" stroke-width="1" class="text-base-content/25" />
        <line x1="7" y1="35" x2="32" y2="35"
          stroke="currentColor" stroke-width="1" class="text-base-content/20" />
      </svg>

      <!-- Name + categories -->
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-1">
          <span class="text-sm font-medium truncate">{{ envelope.envelope_name }}</span>
          <span
            v-if="envelope.rollover"
            class="badge badge-xs badge-info"
            title="Rollover: unspent balance carries forward"
          >↻</span>
        </div>
        <div v-if="categoryLabel" class="text-xs text-base-content/40 truncate">
          {{ categoryLabel }}
        </div>
      </div>

      <!-- ⋮ action button -->
      <div class="relative shrink-0" @click.stop>
        <button
          class="btn btn-ghost btn-xs opacity-40 hover:opacity-100"
          title="Actions"
          @click="toggleMenu"
        >⋮</button>
        <ul
          v-if="menuOpen"
          class="absolute right-0 top-7 z-50 menu menu-sm bg-base-100 border border-base-300 rounded-box shadow-lg w-44 p-1"
        >
          <li>
            <a @click="onAddTransaction">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Add transaction
            </a>
          </li>
          <li>
            <a @click="onEditEnvelope">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit envelope
            </a>
          </li>
        </ul>
      </div>
    </div>

    <!-- Budgeted (editable) -->
    <div class="text-right">
      <template v-if="editing">
        <input
          v-model="inputValue"
          type="number"
          step="0.01"
          class="input input-xs input-bordered w-24 text-right"
          autofocus
          @blur="commitEdit"
          @keyup.enter="commitEdit"
          @keyup.escape="editing = false"
        />
      </template>
      <template v-else>
        <button
          class="btn btn-ghost btn-xs tabular-nums font-normal"
          :class="editedValue === undefined && envelope.is_budget_inherited ? 'italic' : ''"
          :title="editedValue === undefined && envelope.is_budget_inherited
            ? 'Montant hérité du mois précédent — cliquez pour définir le budget de ce mois'
            : 'Cliquez pour modifier le budget'"
          @click.stop="startEdit"
        >
          {{ formatAmount(editedValue ?? envelope.budgeted) }}
          <span
            v-if="editedValue === undefined && envelope.is_budget_inherited"
            class="ml-0.5 text-xs opacity-70"
            aria-label="Hérité du mois précédent"
          >↩</span>
        </button>
      </template>
    </div>

    <!-- Activity -->
    <span
      class="text-right text-sm tabular-nums"
      :class="envelope.activity < 0 ? 'text-error' : envelope.activity > 0 ? 'text-success' : 'text-base-content/40'"
    >
      {{ formatAmount(envelope.activity) }}
    </span>

    <!-- Available -->
    <span class="text-right text-sm tabular-nums" :class="availableClass">
      {{ formatAmount(envelope.available) }}
    </span>
  </div>
</template>