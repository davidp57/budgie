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
}>()

const emit = defineEmits<{
  edit: [value: number]
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
</script>

<template>
  <div
    class="grid grid-cols-[1fr_120px_120px_120px] gap-2 items-center py-1 border-b border-base-300/50 last:border-0"
  >
    <!-- Category name -->
    <span class="text-sm truncate">{{ envelope.category_name }}</span>

    <!-- Budgeted (editable) -->
    <div class="text-right">
      <template v-if="editing">
        <input
          v-model="inputValue"
          type="number"
          step="0.01"
          class="input input-xs input-bordered w-24 text-right"
          @blur="commitEdit"
          @keyup.enter="commitEdit"
          @keyup.escape="editing = false"
          autofocus
        />
      </template>
      <template v-else>
        <button
          class="btn btn-ghost btn-xs tabular-nums font-normal"
          @click="startEdit"
          :title="'Click to edit budgeted amount'"
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
