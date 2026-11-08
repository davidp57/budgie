<script setup lang="ts">
/**
 * RecurringPicker — choose one item in a list, then confirm.
 *
 * Used to pick the line to link with ("Relier à…").
 */

import { computed, ref } from 'vue'

export interface PickerOption {
  id: string
  label: string
}

const props = defineProps<{
  /** Items the user can pick from. */
  options: PickerOption[]
  /** Text before the select ("Même service que :"). */
  prompt: string
  busy: boolean
}>()

const emit = defineEmits<{
  choose: [id: string]
  cancel: []
}>()

const selected = ref('')

// Alphabetical, so that a name is easy to find in a long list
const sorted = computed(() =>
  [...props.options].sort((a, b) => a.label.localeCompare(b.label, 'fr')),
)

function confirm(): void {
  if (selected.value !== '') emit('choose', selected.value)
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2 mt-2" data-test="recurring-picker">
    <span class="text-xs">{{ prompt }}</span>
    <select v-model="selected" class="select select-xs select-bordered max-w-64">
      <option value="" disabled>Choisir…</option>
      <option v-for="o in sorted" :key="o.id" :value="o.id">{{ o.label }}</option>
    </select>
    <button class="btn btn-xs btn-primary" :disabled="busy || selected === ''" @click="confirm">
      Confirmer
    </button>
    <button class="btn btn-xs btn-ghost" @click="emit('cancel')">Annuler</button>
  </div>
</template>
