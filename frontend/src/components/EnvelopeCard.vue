<script setup lang="ts">
/**
 * EnvelopeCard — displays one budget envelope row with inline editing.
 *
 * Props:
 *   envelope    — the EnvelopeLine from the backend
 *   editedValue — centimes override (undefined = use envelope.budgeted)
 *
 * Emits:
 *   edit(centimes) — when the user finishes editing the budgeted amount
 */
import { computed, ref, watch } from 'vue'
import { formatAmount, type EnvelopeLine } from '@/api/types'

const props = defineProps<{
  envelope: EnvelopeLine
  editedValue?: number
  selected?: boolean
}>()

const emit = defineEmits<{
  edit: [value: number]
  select: [envelopeId: number]
}>()

const editing = ref(false)

// Display euros string with 2 decimal places for the input
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

const availableClass = computed(() =>
  props.envelope.available < 0 ? 'text-error font-semibold' : 'text-success',
)

/** e.g. "Groceries · Restaurants" */
const categoryLabel = computed(() =>
  props.envelope.categories.map((c) => c.name).join(' · '),
)

// ── Envelope fill visual ──────────────────────────────────────────
/** Ratio of envelope fill: 0–1. Negative available → 0 (shown red separately). */
const fillRatio = computed<number>(() => {
  const budgeted = props.editedValue ?? props.envelope.budgeted
  if (budgeted <= 0) return props.envelope.available > 0 ? 1 : 0
  return Math.max(0, Math.min(1, props.envelope.available / budgeted))
})

const fillColor = computed<string>(() =>
  props.envelope.available < 0 ? '#f87272' : '#85BB65',
)

const clipId = computed(() => `env-clip-${props.envelope.envelope_id}`)
</script>

<template>
  <div
    class="grid grid-cols-[1fr_120px_120px_120px] gap-2 items-center py-1 border-b border-base-300/50 last:border-0 cursor-pointer rounded transition-colors"
    :class="selected ? 'bg-primary/10' : 'hover:bg-base-200/50'"
    @click="emit('select', envelope.envelope_id)"
  >
    <!-- Envelope name + SVG icon + rollover badge + categories -->
    <div class="min-w-0 flex items-center gap-2">
      <!-- Envelope silhouette SVG -->
      <svg
        viewBox="0 0 40 30"
        width="36"
        height="27"
        class="shrink-0"
        aria-hidden="true"
      >
        <defs>
          <clipPath :id="clipId">
            <path d="M 1 8 L 20 20 L 39 8 L 39 29 L 1 29 Z" />
          </clipPath>
        </defs>
        <!-- Green fill (clipped to envelope shape, rises from bottom) -->
        <rect
          x="1"
          :y="8 + 21 * (1 - fillRatio)"
          width="38"
          :height="21 * fillRatio"
          :fill="fillColor"
          :clip-path="`url(#${clipId})`"
        />
        <!-- Envelope outline -->
        <path
          d="M 1 8 L 20 20 L 39 8 L 39 29 L 1 29 Z"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          class="text-base-content/70"
        />
        <!-- Flap fold line -->
        <path
          d="M 1 8 L 20 20 L 39 8"
          fill="none"
          stroke="currentColor"
          stroke-width="1"
          class="text-base-content/40"
        />
      </svg>

      <div class="min-w-0">
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
          :title="'Click to edit budgeted amount'"
          @click.stop="startEdit"
        >
          {{ formatAmount(editedValue ?? envelope.budgeted) }}
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
