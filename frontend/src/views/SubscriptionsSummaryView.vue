<script setup lang="ts">
/**
 * SubscriptionsSummaryView — what the user pays every month, and for what.
 *
 * The recurring payments the user kept (subscriptions and other recurring
 * payments) that still run, most expensive first, each unfolding on its
 * history and its tags; the totals at the top follow the tag filter. The
 * timeline where lines are classified is one click away, on "Gérer".
 */

import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  createRecurringTag,
  deleteRecurringTag,
  filterByTags,
  formatDay,
  getRecurringSummary,
  localToday,
  summaryTotals,
  tagRecurring,
  tagSubtotals,
  untagRecurring,
} from '@/api/recurring'
import type { RecurringSummary } from '@/api/types'
import { formatAmount } from '@/api/types'
import RecurringSummaryRow from '@/components/RecurringSummaryRow.vue'

const router = useRouter()
const summary = ref<RecurringSummary | null>(null)
const loading = ref(true)
const busy = ref(false)
const selected = ref<number[]>([])
const today = localToday()

const items = computed(() => summary.value?.items ?? [])
const tags = computed(() => summary.value?.tags ?? [])
const shown = computed(() => filterByTags(items.value, selected.value))
const totals = computed(() => summaryTotals(shown.value))
const subtotals = computed(() => tagSubtotals(items.value, tags.value))
const usedTagIds = computed(() => subtotals.value.map((s) => s.tag.id))
const pending = computed(() => {
  const s = summary.value
  if (!s) return []
  const parts: string[] = []
  if (s.to_confirm_count > 0) parts.push(`${s.to_confirm_count} à confirmer`)
  if (s.attention_count > 0) parts.push(`${s.attention_count} à vérifier`)
  return parts
})

function plural(count: number, word: string): string {
  return `${count} ${word}${count > 1 ? 's' : ''}`
}

async function load(): Promise<void> {
  loading.value = true
  try {
    summary.value = await getRecurringSummary()
  } catch {
    // Errors are shown by the client interceptor
  } finally {
    loading.value = false
  }
}

/**
 * Run a change, then show the summary it returns. A filter on a tag no
 * payment carries any more is dropped: its chip is gone, so it could not be
 * cleared otherwise.
 */
async function run(action: () => Promise<RecurringSummary>): Promise<void> {
  busy.value = true
  try {
    summary.value = await action()
    const used = tagSubtotals(summary.value.items, summary.value.tags).map((s) => s.tag.id)
    selected.value = selected.value.filter((id) => used.includes(id))
  } catch {
    // Errors are shown by the client interceptor
  } finally {
    busy.value = false
  }
}

function toggleFilter(tagId: number): void {
  selected.value = selected.value.includes(tagId)
    ? selected.value.filter((id) => id !== tagId)
    : [...selected.value, tagId]
}

function tag(paymentId: number, tagId: number): Promise<void> {
  return run(() => tagRecurring(paymentId, tagId))
}

function untag(paymentId: number, tagId: number): Promise<void> {
  return run(() => untagRecurring(paymentId, tagId))
}

function create(paymentId: number, name: string): Promise<void> {
  return run(async () => {
    const created = await createRecurringTag(name)
    return tagRecurring(paymentId, created.id)
  })
}

function deleteTag(tagId: number): Promise<void> {
  return run(() => deleteRecurringTag(tagId))
}

function manage(): void {
  void router.push({ name: 'abonnements-gerer' })
}

onMounted(load)
</script>

<template>
  <div class="px-4 py-5 lg:px-8 lg:py-6 max-w-3xl mx-auto pb-24">
    <div class="flex items-center justify-between gap-2 mb-4">
      <h1 class="text-xl font-bold">Abonnements</h1>
      <button class="btn btn-sm btn-outline" data-test="manage" @click="manage">
        Gérer
      </button>
    </div>

    <div v-if="loading" class="flex flex-col gap-3">
      <div v-for="i in 3" :key="i" class="skeleton h-20 rounded-2xl" />
    </div>

    <template v-else-if="summary">
      <!-- Nothing kept yet -->
      <div
        v-if="items.length === 0"
        class="text-center py-12 text-base-content/60"
        data-test="summary-empty"
      >
        <p class="text-5xl mb-4">🔁</p>
        <p class="font-medium">Aucun paiement récurrent en cours n'est encore classé</p>
        <p class="text-sm mt-1 mb-4">
          Classe tes lignes dans « Gérer » : les abonnements et les autres paiements
          réguliers que tu gardes apparaîtront ici.
        </p>
        <button class="btn btn-primary btn-sm" @click="manage">Gérer mes abonnements</button>
      </div>

      <template v-else>
        <!-- Totals -->
        <div class="card bg-base-100 border border-base-300 mb-3">
          <div class="card-body p-4 gap-1">
            <p class="text-2xl font-bold tabular-nums" data-test="summary-total">
              {{ formatAmount(totals.monthly) }}<span class="text-sm font-normal text-base-content/50"> / mois</span>
              <span class="block text-sm font-normal text-base-content/60">
                soit {{ formatAmount(totals.yearly) }} par an · {{ plural(shown.length, 'paiement') }}
              </span>
            </p>
            <p class="text-sm tabular-nums" data-test="summary-subscriptions">
              Dont abonnements : <span class="font-semibold">{{ formatAmount(totals.subscriptionsMonthly) }}</span>/mois
              <span class="text-base-content/60">({{ formatAmount(totals.subscriptionsYearly) }} par an)</span>
            </p>
            <p v-if="summary.as_of < today" class="text-xs text-base-content/50">
              Situation au {{ formatDay(summary.as_of) }}, date du dernier prélèvement importé.
            </p>
          </div>
        </div>

        <!-- What is left to do in "Gérer" -->
        <button
          v-if="pending.length > 0"
          type="button"
          class="alert alert-info alert-soft text-sm py-2 mb-3 w-full text-left"
          data-test="summary-pending"
          @click="manage"
        >
          <span class="flex-1">{{ pending.join(' · ') }} dans « Gérer »</span>
          <span aria-hidden="true">→</span>
        </button>

        <!-- Tag filters -->
        <div v-if="subtotals.length > 0" class="flex flex-wrap gap-2 mb-3" role="group" aria-label="Filtrer par étiquette">
          <button
            type="button"
            class="btn btn-xs rounded-full"
            :class="selected.length === 0 ? 'btn-primary' : 'btn-ghost border-base-300'"
            :aria-pressed="selected.length === 0"
            data-test="tag-filter-all"
            @click="selected = []"
          >Tout</button>
          <button
            v-for="sub in subtotals"
            :key="sub.tag.id"
            type="button"
            class="btn btn-xs rounded-full tabular-nums"
            :class="selected.includes(sub.tag.id) ? 'btn-primary' : 'btn-ghost border-base-300'"
            :aria-pressed="selected.includes(sub.tag.id)"
            data-test="tag-filter"
            @click="toggleFilter(sub.tag.id)"
          >{{ sub.tag.name }} · {{ formatAmount(sub.monthly) }}</button>
        </div>

        <ul class="flex flex-col gap-2">
          <RecurringSummaryRow
            v-for="item in shown"
            :key="item.id"
            :item="item"
            :tags="tags"
            :used-tag-ids="usedTagIds"
            :busy="busy"
            @tag="tag"
            @untag="untag"
            @create="create"
            @delete-tag="deleteTag"
          />
        </ul>
      </template>
    </template>
  </div>
</template>
