<script setup lang="ts">
/**
 * RecurringLabels — the bank labels merged into a payment, each detachable.
 */

import type { RecurringPayment } from '@/api/types'
import { formatAmount } from '@/api/types'
import { defaultName } from '@/api/recurring'

defineProps<{
  payment: RecurringPayment
  busy: boolean
}>()

const emit = defineEmits<{
  detach: [aliasId: number]
}>()
</script>

<template>
  <div v-if="payment.aliases.length > 0" class="flex flex-wrap items-center gap-1 text-xs text-base-content/60">
    <span>Aussi prélevé sous :</span>
    <span
      v-for="a in payment.aliases"
      :key="a.id"
      class="badge badge-ghost badge-sm gap-1"
      data-test="recurring-alias"
    >
      {{ defaultName(a.key) }} ({{ formatAmount(a.amount) }})
      <button
        class="opacity-60 hover:opacity-100"
        :disabled="busy"
        :title="`Détacher ${defaultName(a.key)}`"
        :aria-label="`Détacher ${defaultName(a.key)}`"
        @click="emit('detach', a.id)"
      >✕</button>
    </span>
  </div>
</template>
