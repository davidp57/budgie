<script setup lang="ts">
/**
 * RecurringPicker — choose a classified payment, then confirm.
 *
 * Used for "same as…" on a candidate and "merge with…" on a payment.
 */

import { computed, ref } from 'vue'
import type { RecurringPayment } from '@/api/types'
import { formatAmount } from '@/api/types'
import { periodLabel } from '@/api/recurring'

const props = defineProps<{
  /** Payments the user can pick from. */
  payments: RecurringPayment[]
  /** Text before the select ("Même paiement que :", "<name> absorbe :"). */
  prompt: string
  busy: boolean
}>()

const emit = defineEmits<{
  choose: [paymentId: number]
  cancel: []
}>()

const selected = ref<number | ''>('')

// Alphabetical, so that a name is easy to find in a long list
const sorted = computed(() =>
  [...props.payments].sort((a, b) => a.name.localeCompare(b.name, 'fr')),
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
      <option v-for="p in sorted" :key="p.id" :value="p.id">
        {{ p.name }} — {{ formatAmount(p.current_amount) }} · {{ periodLabel(p.period) }}
      </option>
    </select>
    <button class="btn btn-xs btn-primary" :disabled="busy || selected === ''" @click="confirm">
      Confirmer
    </button>
    <button class="btn btn-xs btn-ghost" @click="emit('cancel')">Annuler</button>
  </div>
</template>
