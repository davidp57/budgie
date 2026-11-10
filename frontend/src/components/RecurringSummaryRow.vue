<script setup lang="ts">
/**
 * RecurringSummaryRow — one running recurring payment on the presentation
 * page: its name, tags, monthly cost and since when; it unfolds on its
 * history (successive prices, every debit) and on its tags.
 */

import { computed, ref } from 'vue'
import type { RecurringSummaryItem, RecurringTag } from '@/api/types'
import { formatAmount } from '@/api/types'
import { formatDay, formatMonth, periodLabel, sinceLabel } from '@/api/recurring'
import RecurringTagEditor from '@/components/RecurringTagEditor.vue'

const props = defineProps<{
  item: RecurringSummaryItem
  tags: RecurringTag[]
  usedTagIds: number[]
  busy: boolean
}>()

const emit = defineEmits<{
  tag: [paymentId: number, tagId: number]
  untag: [paymentId: number, tagId: number]
  create: [paymentId: number, name: string]
  deleteTag: [tagId: number]
}>()

const open = ref(false)

const itemTags = computed(() => props.tags.filter((t) => props.item.tag_ids.includes(t.id)))

/** Prices most recent first: the current one "since", the earlier ones "from… to…". */
const prices = computed(() =>
  [...props.item.segments].reverse().map((s, index) => ({
    key: `${s.start}-${s.amount}`,
    amount: s.amount,
    count: s.count,
    when:
      index === 0
        ? sinceLabel(s.start)
        : s.start.slice(0, 7) === s.end.slice(0, 7)
          ? `en ${formatMonth(s.start)}`
          : `de ${formatMonth(s.start)} à ${formatMonth(s.end)}`,
  })),
)
</script>

<template>
  <li class="card bg-base-100 border border-base-300" data-test="summary-row">
    <button
      type="button"
      class="w-full text-left px-4 py-3 flex items-start gap-3"
      :aria-expanded="open"
      data-test="summary-toggle"
      @click="open = !open"
    >
      <div class="flex-1 min-w-0">
        <p class="font-semibold truncate">{{ item.name }}</p>
        <p class="text-xs text-base-content/60">
          {{ periodLabel(item.period) }} · {{ sinceLabel(item.first_date) }}
          <span v-if="item.kind === 'other'"> · pas un abonnement</span>
        </p>
        <div v-if="itemTags.length > 0" class="flex flex-wrap gap-1 mt-1">
          <span v-for="tag in itemTags" :key="tag.id" class="badge badge-sm badge-ghost">
            {{ tag.name }}
          </span>
        </div>
      </div>
      <div class="text-right shrink-0">
        <p class="font-semibold tabular-nums">
          {{ formatAmount(item.monthly_cost) }}<span class="text-xs font-normal text-base-content/50">/mois</span>
        </p>
        <p v-if="item.period !== 'monthly'" class="text-xs text-base-content/60 tabular-nums">
          {{ formatAmount(item.amount) }} {{ periodLabel(item.period) }}
        </p>
      </div>
      <span class="text-base-content/40 mt-0.5" aria-hidden="true">{{ open ? '▴' : '▾' }}</span>
    </button>

    <div v-if="open" class="px-4 pb-4 flex flex-col gap-4" data-test="summary-history">
      <section>
        <h3 class="text-xs font-semibold uppercase text-base-content/50 mb-1.5">Étiquettes</h3>
        <RecurringTagEditor
          :tags="tags"
          :selected="item.tag_ids"
          :used-tag-ids="usedTagIds"
          :busy="busy"
          @tag="(tagId) => emit('tag', item.id, tagId)"
          @untag="(tagId) => emit('untag', item.id, tagId)"
          @create="(name) => emit('create', item.id, name)"
          @delete="(tagId) => emit('deleteTag', tagId)"
        />
      </section>

      <section>
        <h3 class="text-xs font-semibold uppercase text-base-content/50 mb-1.5">Tarifs</h3>
        <ul class="text-sm flex flex-col gap-0.5">
          <li
            v-for="price in prices"
            :key="price.key"
            class="flex justify-between gap-2"
            data-test="summary-price"
          >
            <span class="tabular-nums font-medium">{{ formatAmount(price.amount) }}</span>
            <span class="text-base-content/60 text-right">
              {{ price.when }} · {{ price.count }} prélèvement{{ price.count > 1 ? 's' : '' }}
            </span>
          </li>
        </ul>
      </section>

      <section>
        <h3 class="text-xs font-semibold uppercase text-base-content/50 mb-1.5">
          Prélèvements ({{ item.occurrences }})
        </h3>
        <ul class="text-sm max-h-48 overflow-y-auto divide-y divide-base-200">
          <li
            v-for="debit in item.debits"
            :key="debit.date + debit.amount"
            class="flex justify-between py-1 pr-1"
            data-test="summary-debit"
          >
            <span class="tabular-nums">{{ formatDay(debit.date) }}</span>
            <span class="tabular-nums">{{ formatAmount(debit.amount) }}</span>
          </li>
        </ul>
      </section>
    </div>
  </li>
</template>
