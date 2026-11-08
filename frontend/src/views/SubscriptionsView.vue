<script setup lang="ts">
/**
 * SubscriptionsView — what recurring debits cost now, and their history.
 *
 * "En ce moment" starts from the answer: every recurring payment that still
 * runs, classified or not, with the monthly total; classifying is a
 * correction ("not a subscription", "cancelled", rename), never a
 * prerequisite. "Historique" shows one line per service over two years,
 * successive prices on the same line, and links lines when a debit was
 * renamed.
 */

import { computed, onMounted, ref } from 'vue'
import {
  acceptRecurringPrice,
  attentionLines,
  classifyLine,
  detachRecurring,
  forgetRecurring,
  formatDay,
  getRecurringBoard,
  lineGroup,
  linkLines,
  localToday,
  periodLabel,
  renameKind,
  resetRecurring,
  updateRecurring,
} from '@/api/recurring'
import type { LineAction, LineGroup } from '@/api/recurring'
import { listCategoryGroups } from '@/api/categories'
import type { CategoryGroupWithCategories, RecurringBoard, RecurringLine } from '@/api/types'
import { formatAmount } from '@/api/types'
import RecurringLabels from '@/components/RecurringLabels.vue'
import RecurringTimeline from '@/components/RecurringTimeline.vue'

const board = ref<RecurringBoard | null>(null)
const groups = ref<CategoryGroupWithCategories[]>([])
const loading = ref(true)
const busy = ref(false)
// The timeline is the main view (David, 2026-11-08)
const tab = ref<'now' | 'history'>('history')
const today = localToday()

// Inline edits
const renamingId = ref<string | null>(null)
const renameValue = ref('')
const cancellingId = ref<string | null>(null)
const cancelDate = ref('')
const detailsId = ref<string | null>(null)
const confirmingReset = ref(false)

const lines = computed(() => board.value?.lines ?? [])
function inGroup(group: LineGroup): RecurringLine[] {
  return lines.value.filter((l) => lineGroup(l) === group)
}
const toCheck = computed(() => inGroup('check'))
const running = computed(() => inGroup('subscription'))
const others = computed(() => inGroup('other'))
const stopped = computed(() => inGroup('stopped'))
const ignored = computed(() => inGroup('ignored'))
// Ignored lines stay on the timeline, faded, so that they can be proposed again
const timelineLines = computed(() => lines.value.filter((l) => l.segments.length > 0))
const classifiedCount = computed(() => lines.value.filter((l) => l.payment).length)

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

/** Run one correction on a line, from either tab. */
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

function confirmSubscription(line: RecurringLine): Promise<void> {
  return perform(line, { type: 'kind', kind: 'subscription' })
}

function notSubscription(line: RecurringLine): Promise<void> {
  return perform(line, { type: 'kind', kind: 'other' })
}

function ignore(line: RecurringLine): Promise<void> {
  return perform(line, { type: 'kind', kind: 'dismissed' })
}

function forget(line: RecurringLine): Promise<void> {
  detailsId.value = null
  return perform(line, { type: 'forget' })
}

function startRename(line: RecurringLine): void {
  renamingId.value = line.id
  renameValue.value = line.name
}

async function saveRename(line: RecurringLine): Promise<void> {
  // Enter then blur both call this: only the first one saves
  if (renamingId.value !== line.id) return
  const name = renameValue.value.trim()
  renamingId.value = null
  if (name && name !== line.name) await perform(line, { type: 'rename', name })
}

function startCancel(line: RecurringLine): void {
  cancellingId.value = line.id
  cancelDate.value = today
}

async function confirmCancel(line: RecurringLine): Promise<void> {
  const date = cancelDate.value
  cancellingId.value = null
  if (date) await perform(line, { type: 'cancel', date })
}

function onCategoryChange(line: RecurringLine, event: Event): void {
  const value = (event.target as HTMLSelectElement).value
  void perform(line, { type: 'category', categoryId: value ? Number(value) : null })
}

function acceptPrice(line: RecurringLine): Promise<void> {
  return perform(line, { type: 'acceptPrice' })
}

function uncancel(line: RecurringLine): Promise<void> {
  return perform(line, { type: 'cancel', date: null })
}

function detach(line: RecurringLine, aliasId: number): Promise<void> {
  return perform(line, { type: 'detach', aliasId })
}

function link(earlierId: string, laterId: string): Promise<void> {
  const earlier = lines.value.find((l) => l.id === earlierId)
  const later = lines.value.find((l) => l.id === laterId)
  if (!earlier || !later) return Promise.resolve()
  return run(() => linkLines(earlier.ref, later.ref))
}

async function reset(): Promise<void> {
  confirmingReset.value = false
  await run(() => resetRecurring())
}

function attentionText(line: RecurringLine): string[] {
  return line.payment ? attentionLines(line.payment) : []
}

onMounted(load)
</script>

<template>
  <div class="px-4 py-5 lg:px-8 lg:py-6 max-w-5xl mx-auto pb-24">
    <h1 class="text-xl font-bold mb-4">Abonnements</h1>

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
              {{ running.length }} abonnement{{ running.length > 1 ? 's' : '' }} en cours
            </p>
            <p v-if="board.as_of < today" class="text-xs text-base-content/50 mt-1" data-test="as-of">
              Situation au {{ formatDay(board.as_of) }}, date du dernier prélèvement importé.
            </p>
            <p v-if="board.estimated_count > 0" class="text-xs text-base-content/50 mt-1">
              Dont {{ board.estimated_count }} repéré{{ board.estimated_count > 1 ? 's' : '' }}
              automatiquement : confirme-les ou écarte-les ci-dessous.
            </p>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div role="tablist" class="tabs tabs-box mb-4 w-fit">
        <button
          role="tab"
          class="tab"
          :class="{ 'tab-active': tab === 'history' }"
          data-test="tab-history"
          @click="tab = 'history'"
        >
          Historique
          <span v-if="board.suggestions.length > 0" class="badge badge-warning badge-xs ml-1">
            {{ board.suggestions.length }}
          </span>
        </button>
        <button
          role="tab"
          class="tab"
          :class="{ 'tab-active': tab === 'now' }"
          data-test="tab-now"
          @click="tab = 'now'"
        >
          En ce moment
        </button>
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

      <!-- ══ Now ══ -->
      <template v-else-if="tab === 'now'">
        <!-- Needs a look -->
        <section v-if="toCheck.length > 0" class="mb-6">
          <h2 class="font-semibold mb-2">⚠️ À vérifier</h2>
          <div class="flex flex-col gap-2">
            <div
              v-for="line in toCheck"
              :key="line.id"
              class="rounded-xl border border-warning bg-warning/10 p-3"
            >
              <div class="flex items-center gap-2">
                <span class="font-medium flex-1">{{ line.name }}</span>
                <span class="text-sm tabular-nums">{{ formatAmount(line.amount) }} · {{ periodLabel(line.period) }}</span>
              </div>
              <p v-for="t in attentionText(line)" :key="t" class="text-sm mt-1">{{ t }}</p>
              <div class="flex flex-wrap gap-2 mt-2">
                <button
                  v-if="line.payment?.price_changed && line.payment.status !== 'cancelled'"
                  class="btn btn-xs"
                  :disabled="busy"
                  @click="acceptPrice(line)"
                >Accepter le nouveau prix</button>
                <button
                  v-if="line.payment?.status === 'probably_ended'"
                  class="btn btn-xs"
                  :disabled="busy"
                  @click="startCancel(line)"
                >Marquer résilié</button>
                <button
                  v-if="line.payment?.cancelled_at"
                  class="btn btn-xs btn-ghost"
                  :disabled="busy"
                  @click="uncancel(line)"
                >Annuler la résiliation</button>
                <button class="btn btn-xs btn-ghost" @click="tab = 'history'">Voir l'historique</button>
              </div>
              <div v-if="cancellingId === line.id" class="flex items-center gap-2 mt-2">
                <span class="text-xs">Résilié le</span>
                <input v-model="cancelDate" type="date" class="input input-xs input-bordered" />
                <button class="btn btn-xs btn-primary" :disabled="busy" @click="confirmCancel(line)">Confirmer</button>
                <button class="btn btn-xs btn-ghost" @click="cancellingId = null">Annuler</button>
              </div>
            </div>
          </div>
        </section>

        <!-- Running subscriptions -->
        <section class="mb-6">
          <h2 class="font-semibold mb-2">Abonnements en cours ({{ running.length }})</h2>
          <p v-if="running.length === 0" class="text-sm text-base-content/50">Aucun.</p>
          <div
            v-else
            class="flex flex-col divide-y divide-base-300 rounded-xl border border-base-300 bg-base-100"
          >
            <div
              v-for="line in running"
              :key="line.id"
              class="p-3 flex flex-col gap-1"
              data-test="running-line"
            >
              <div class="flex items-center gap-2">
                <input
                  v-if="renamingId === line.id"
                  v-model="renameValue"
                  class="input input-sm input-bordered flex-1"
                  maxlength="200"
                  @keydown.enter="saveRename(line)"
                  @blur="saveRename(line)"
                />
                <button
                  v-else
                  class="font-medium flex-1 text-left min-w-0 truncate"
                  title="Renommer"
                  @click="startRename(line)"
                >
                  {{ line.name }} <span class="text-base-content/30 text-xs">✏️</span>
                </button>
                <span
                  v-if="!line.payment"
                  class="badge badge-ghost badge-sm"
                  title="Repéré automatiquement, pas encore confirmé"
                >à confirmer</span>
                <span class="tabular-nums font-semibold">{{ formatAmount(line.monthly_cost) }}<span class="text-xs font-normal text-base-content/50">/mois</span></span>
              </div>
              <p class="text-xs text-base-content/60">
                {{ formatAmount(line.amount) }} · {{ periodLabel(line.period) }}
                <template v-if="line.last_date"> · dernier prélèvement le {{ formatDay(line.last_date) }}</template>
                <template v-if="line.segments.length > 1"> · {{ line.segments.length }} tarifs successifs</template>
              </p>
              <div class="flex flex-wrap items-center gap-2 mt-1">
                <button
                  v-if="!line.payment"
                  class="btn btn-xs btn-primary"
                  :disabled="busy"
                  @click="confirmSubscription(line)"
                  title="C'est bien un abonnement"
                >✓ Confirmer</button>
                <button class="btn btn-xs" :disabled="busy" @click="notSubscription(line)">Pas un abonnement</button>
                <button class="btn btn-xs" :disabled="busy" @click="startCancel(line)">Résilié…</button>
                <button
                  v-if="line.payment"
                  class="btn btn-xs btn-ghost"
                  @click="detailsId = detailsId === line.id ? null : line.id"
                >{{ detailsId === line.id ? 'Moins' : 'Plus…' }}</button>
              </div>
              <div v-if="cancellingId === line.id" class="flex items-center gap-2 mt-1">
                <span class="text-xs">Résilié le</span>
                <input v-model="cancelDate" type="date" class="input input-xs input-bordered" />
                <button class="btn btn-xs btn-primary" :disabled="busy" @click="confirmCancel(line)">Confirmer</button>
                <button class="btn btn-xs btn-ghost" @click="cancellingId = null">Annuler</button>
              </div>
              <div v-if="detailsId === line.id && line.payment" class="flex flex-col gap-2 mt-1">
                <div class="flex flex-wrap items-center gap-2">
                  <select
                    class="select select-xs select-bordered max-w-48"
                    :value="line.payment.category_id ?? ''"
                    :disabled="busy"
                    @change="onCategoryChange(line, $event)"
                  >
                    <option value="">Sans catégorie</option>
                    <optgroup v-for="g in groups" :key="g.id" :label="g.name">
                      <option v-for="c in g.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                    </optgroup>
                  </select>
                  <button class="btn btn-xs btn-ghost" :disabled="busy" @click="forget(line)">Retirer le classement</button>
                </div>
                <RecurringLabels :payment="line.payment" :busy="busy" @detach="(id) => detach(line, id)" />
              </div>
            </div>
          </div>
        </section>

        <!-- Probably not subscriptions -->
        <details v-if="others.length > 0" class="mb-4">
          <summary class="font-semibold cursor-pointer">
            Probablement pas des abonnements ({{ others.length }})
          </summary>
          <p class="text-xs text-base-content/60 mt-1">
            Virements, impôts, épargne, assurances… : hors du total.
          </p>
          <div class="flex flex-col gap-1 mt-2">
            <div
              v-for="line in others"
              :key="line.id"
              class="flex flex-wrap items-center gap-2 text-sm px-1"
            >
              <span class="flex-1 min-w-0 truncate" :title="line.label ?? line.name">{{ line.name }}</span>
              <span class="text-base-content/60 tabular-nums">{{ formatAmount(line.amount) }} · {{ periodLabel(line.period) }}</span>
              <button class="btn btn-xs btn-ghost" :disabled="busy" @click="confirmSubscription(line)">C'est un abonnement</button>
            </div>
          </div>
        </details>

        <!-- Stopped -->
        <details v-if="stopped.length > 0" class="mb-4">
          <summary class="font-semibold cursor-pointer">Arrêtés ({{ stopped.length }})</summary>
          <p class="text-xs text-base-content/60 mt-1">
            Plus prélevés depuis plus d'une période et demie. L'Historique montre ce qui les a remplacés.
          </p>
          <div class="flex flex-col gap-1 mt-2">
            <div
              v-for="line in stopped"
              :key="line.id"
              class="flex flex-wrap items-center gap-2 text-sm px-1"
            >
              <span class="flex-1 min-w-0 truncate">{{ line.name }}</span>
              <span class="text-base-content/60 tabular-nums">{{ formatAmount(line.amount) }} · {{ periodLabel(line.period) }}</span>
              <span v-if="line.last_date" class="text-xs text-base-content/50">dernier le {{ formatDay(line.last_date) }}</span>
              <button v-if="!line.payment" class="btn btn-xs btn-ghost" :disabled="busy" @click="ignore(line)">Ignorer</button>
            </div>
          </div>
        </details>

        <!-- Ignored -->
        <details v-if="ignored.length > 0" class="mb-4">
          <summary class="font-semibold cursor-pointer">Ignorés ({{ ignored.length }})</summary>
          <div class="flex flex-col gap-1 mt-2">
            <div v-for="line in ignored" :key="line.id" class="flex items-center gap-2 text-sm px-1">
              <span class="flex-1">{{ line.name }}</span>
              <span class="text-base-content/60 tabular-nums">{{ formatAmount(line.amount) }} · {{ periodLabel(line.period) }}</span>
              <button class="btn btn-xs btn-ghost" :disabled="busy" @click="forget(line)">Reproposer</button>
            </div>
          </div>
        </details>
      </template>

      <!-- ══ History ══ -->
      <template v-else>
        <p class="text-xs text-base-content/60 mb-3">
          Une ligne par service sur deux ans, du premier au dernier prélèvement ; ses tarifs
          successifs sont sur la même ligne. Quand un libellé a changé, « Relier à… » réunit
          les deux lignes ; Budgie suggère celles qui se suivent au même montant exact.
        </p>
        <RecurringTimeline
          :lines="timelineLines"
          :suggestions="board.suggestions"
          :today="board.as_of"
          :cancel-default="today"
          :groups="groups"
          :busy="busy"
          @link="link"
          @action="performOn"
        />
      </template>

      <!-- Reset -->
      <div v-if="classifiedCount > 0" class="mt-8 pt-4 border-t border-base-300">
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
            <template v-if="classifiedCount > 1">Effacer tes {{ classifiedCount }} classements</template>
            <template v-else>Effacer ton classement</template>
            (abonnements confirmés, « pas un abonnement », ignorés, libellés reliés, résiliations) ?
            Les transactions importées ne sont pas touchées : l'écran repart de la détection seule.
            Ce n'est pas réversible.
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
