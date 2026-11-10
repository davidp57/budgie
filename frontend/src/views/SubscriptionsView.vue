<script setup lang="ts">
/**
 * SubscriptionsView — the "Gérer" page: where recurring debits are
 * classified, as one timeline. The presentation of what runs is the
 * subscriptions page itself (SubscriptionsSummaryView).
 *
 * The total of the running subscriptions at the top, then one line per
 * service over two years (successive prices on the same line), each with its
 * status, alerts and corrections; what is not a subscription and what was
 * ignored are folded below. Classifying is a correction, never a
 * prerequisite: the total counts detected lines until told otherwise.
 */

import { computed, onMounted, ref } from 'vue'
import {
  acceptRecurringPrice,
  classifyLine,
  countsInTotal,
  detachRecurring,
  forgetRecurring,
  formatDay,
  getRecurringBoard,
  linkLines,
  localToday,
  refuseLink,
  renameKind,
  resetRecurring,
  updateRecurring,
} from '@/api/recurring'
import type { LineAction } from '@/api/recurring'
import { listCategoryGroups } from '@/api/categories'
import type { CategoryGroupWithCategories, RecurringBoard, RecurringLine } from '@/api/types'
import { formatAmount } from '@/api/types'
import RecurringTimeline from '@/components/RecurringTimeline.vue'

const board = ref<RecurringBoard | null>(null)
const groups = ref<CategoryGroupWithCategories[]>([])
const loading = ref(true)
const busy = ref(false)
const today = localToday()
const confirmingReset = ref(false)

const lines = computed(() => board.value?.lines ?? [])
const runningCount = computed(() => lines.value.filter(countsInTotal).length)
const timelineLines = computed(() => lines.value.filter((l) => l.segments.length > 0))
const classifiedCount = computed(() => lines.value.filter((l) => l.payment).length)
// Something to reset: a classification, or a refused suggestion
const resettable = computed(() => classifiedCount.value + (board.value?.refused_count ?? 0) > 0)

async function load(): Promise<void> {
  loading.value = true
  try {
    const [b, g] = await Promise.all([getRecurringBoard(), listCategoryGroups()])
    board.value = b
    groups.value = g
  } catch {
    // Errors are shown by the client interceptor
  } finally {
    loading.value = false
  }
}

async function run(action: () => Promise<RecurringBoard | void>): Promise<void> {
  busy.value = true
  try {
    const result = await action()
    board.value = result ?? (await getRecurringBoard())
  } catch {
    // Errors are shown by the client interceptor
  } finally {
    busy.value = false
  }
}

/** Run one correction on a line. */
function perform(line: RecurringLine, action: LineAction): Promise<void> {
  const p = line.payment
  switch (action.type) {
    case 'kind':
      return run(() =>
        p ? updateRecurring(p.id, { kind: action.kind }) : classifyLine(line, action.kind),
      )
    case 'rename':
      return run(() =>
        p
          ? updateRecurring(p.id, { name: action.name })
          : classifyLine(line, renameKind(line), action.name),
      )
    case 'cancel':
      if (p) return run(() => updateRecurring(p.id, { cancelled_at: action.date }))
      if (!action.date) return Promise.resolve()
      return run(() => classifyLine(line, 'subscription', line.name, action.date))
    case 'forget':
      return p ? run(() => forgetRecurring(p.id)) : Promise.resolve()
    case 'acceptPrice':
      return p ? run(() => acceptRecurringPrice(p.id)) : Promise.resolve()
    case 'category':
      return p
        ? run(() => updateRecurring(p.id, { category_id: action.categoryId }))
        : Promise.resolve()
    case 'detach':
      return p ? run(() => detachRecurring(p.id, action.aliasId)) : Promise.resolve()
  }
}

function performOn(lineId: string, action: LineAction): Promise<void> {
  const line = lines.value.find((l) => l.id === lineId)
  return line ? perform(line, action) : Promise.resolve()
}

function link(earlierId: string, laterId: string): Promise<void> {
  const earlier = lines.value.find((l) => l.id === earlierId)
  const later = lines.value.find((l) => l.id === laterId)
  if (!earlier || !later) return Promise.resolve()
  return run(() => linkLines(earlier.ref, later.ref))
}

function refuse(earlierId: string, laterId: string): Promise<void> {
  const earlier = lines.value.find((l) => l.id === earlierId)
  const later = lines.value.find((l) => l.id === laterId)
  if (!earlier || !later) return Promise.resolve()
  return run(() => refuseLink(earlier.key, later.key))
}

async function reset(): Promise<void> {
  confirmingReset.value = false
  await run(() => resetRecurring())
}

onMounted(load)
</script>

<template>
  <div class="px-4 py-5 lg:px-8 lg:py-6 max-w-5xl mx-auto pb-24">
    <div class="flex items-center gap-2 mb-4">
      <RouterLink
        :to="{ name: 'abonnements' }"
        class="btn btn-ghost btn-sm btn-circle"
        aria-label="Retour à la présentation des abonnements"
        data-test="back-to-summary"
      >←</RouterLink>
      <h1 class="text-xl font-bold">Gérer les abonnements</h1>
    </div>

    <div v-if="loading" class="flex flex-col gap-3">
      <div v-for="i in 3" :key="i" class="skeleton h-20 rounded-2xl" />
    </div>

    <template v-else-if="board">
      <!-- Totals -->
      <div class="card bg-base-100 border border-base-300 mb-4">
        <div class="card-body p-4 flex-row items-center gap-4">
          <span class="text-3xl">🔁</span>
          <div class="flex-1">
            <p class="text-2xl font-bold tabular-nums" data-test="monthly-total">
              {{ formatAmount(board.monthly_total) }}<span class="text-sm font-normal text-base-content/50"> / mois</span>
            </p>
            <p class="text-sm text-base-content/60 tabular-nums">
              soit {{ formatAmount(board.yearly_total) }} par an ·
              {{ runningCount }} abonnement{{ runningCount > 1 ? 's' : '' }} en cours
            </p>
            <p v-if="board.as_of < today" class="text-xs text-base-content/50 mt-1" data-test="as-of">
              Situation au {{ formatDay(board.as_of) }}, date du dernier prélèvement importé.
            </p>
            <p v-if="board.estimated_count > 0" class="text-xs text-base-content/50 mt-1">
              Dont {{ board.estimated_count }} repéré{{ board.estimated_count > 1 ? 's' : '' }}
              automatiquement (« à confirmer » ci-dessous).
            </p>
            <p v-if="board.attention_count > 0" class="text-xs text-warning mt-1" data-test="attention">
              {{ board.attention_count }} abonnement{{ board.attention_count > 1 ? 's' : '' }}
              à vérifier, signalé{{ board.attention_count > 1 ? 's' : '' }} dans la liste.
            </p>
          </div>
        </div>
      </div>

      <!-- Nothing found -->
      <div v-if="lines.length === 0" class="text-center py-12 text-base-content/50">
        <p class="text-5xl mb-4">🔍</p>
        <p class="font-medium">Aucun paiement récurrent trouvé</p>
        <p class="text-sm mt-1">
          Importe tes relevés bancaires : il faut au moins trois prélèvements réguliers
          (deux pour un abonnement annuel) pour en repérer un.
        </p>
      </div>

      <template v-else>
        <p class="text-xs text-base-content/60 mb-3">
          Une ligne par service sur deux ans, du premier au dernier prélèvement ; ses tarifs
          successifs sont sur la même ligne. Classe, renomme ou résilie depuis chaque ligne ;
          « relier à… » réunit deux libellés d'un même service.
        </p>
        <RecurringTimeline
          :lines="timelineLines"
          :suggestions="board.suggestions"
          :today="board.as_of"
          :cancel-default="today"
          :groups="groups"
          :busy="busy"
          @link="link"
          @refuse="refuse"
          @action="performOn"
        />
      </template>

      <!-- Reset -->
      <div v-if="resettable" class="mt-8 pt-4 border-t border-base-300">
        <button
          class="btn btn-sm btn-ghost text-error"
          :disabled="busy"
          data-test="reset"
          @click="confirmingReset = true"
        >Réinitialiser les classements…</button>
        <div
          v-if="confirmingReset"
          class="alert alert-warning mt-2 flex-col items-start"
          data-test="reset-confirm"
        >
          <p class="text-sm">
            Effacer tous tes classements (abonnements confirmés, « pas un abonnement », ignorés,
            libellés reliés, résiliations, étiquettes) et tes suggestions refusées ? Les transactions importées
            ne sont pas touchées : la page repart de la détection seule. Ce n'est pas réversible.
          </p>
          <div class="flex gap-2">
            <button class="btn btn-sm btn-error" :disabled="busy" @click="reset">Tout effacer</button>
            <button class="btn btn-sm btn-ghost" @click="confirmingReset = false">Annuler</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
