<script setup lang="ts">
/**
 * SubscriptionsView — recurring debits found in the imported transactions.
 *
 * Candidates are classified by the user (subscription, other recurring
 * payment, or ignored); subscriptions show their monthly and yearly cost,
 * and those that need a look (stopped, debited after cancellation, new
 * price) are listed first.
 *
 * The candidates can be narrowed to the recent ones, to work through a long
 * history piece by piece, and a candidate or a payment can be merged into
 * another payment when the bank or the merchant renamed the debit.
 */

import { computed, onMounted, ref } from 'vue'
import {
  SINCE_CHOICES,
  acceptRecurringPrice,
  attachRecurring,
  classifyRecurring,
  defaultName,
  detachRecurring,
  filterSince,
  forgetRecurring,
  formatDay,
  getRecurringOverview,
  listRecurringCandidates,
  localToday,
  mergeRecurring,
  needsAttention,
  periodLabel,
  updateRecurring,
} from '@/api/recurring'
import type { RecurringUpdate } from '@/api/recurring'
import { listCategoryGroups } from '@/api/categories'
import type {
  CategoryGroupWithCategories,
  RecurringCandidate,
  RecurringKind,
  RecurringOverview,
  RecurringPayment,
} from '@/api/types'
import { formatAmount } from '@/api/types'
import RecurringLabels from '@/components/RecurringLabels.vue'
import RecurringPicker from '@/components/RecurringPicker.vue'

const overview = ref<RecurringOverview | null>(null)
const candidates = ref<RecurringCandidate[]>([])
const groups = ref<CategoryGroupWithCategories[]>([])
const loading = ref(true)
const busy = ref(false)

// Inline edits
const renamingId = ref<number | null>(null)
const renameValue = ref('')
const cancellingId = ref<number | null>(null)
const cancelDate = ref('')
const mergingCandidate = ref<string | null>(null)
const mergingPaymentId = ref<number | null>(null)

// Candidates last debited within this many months (0 = all)
const sinceMonths = ref(3)

const payments = computed(() => overview.value?.payments ?? [])
const subscriptions = computed(() => payments.value.filter((p) => p.kind === 'subscription'))
const toCheck = computed(() => subscriptions.value.filter(needsAttention))
const active = computed(() =>
  subscriptions.value.filter((p) => p.status === 'active' && !needsAttention(p)),
)
const stopped = computed(() =>
  subscriptions.value.filter((p) => p.status !== 'active' && !needsAttention(p)),
)
const activeCount = computed(
  () => subscriptions.value.filter((p) => p.status === 'active').length,
)
const others = computed(() => payments.value.filter((p) => p.kind === 'other'))
const dismissed = computed(() => payments.value.filter((p) => p.kind === 'dismissed'))
const nothingYet = computed(() => payments.value.length === 0 && candidates.value.length === 0)
const shownCandidates = computed(() =>
  filterSince(candidates.value, sinceMonths.value, localToday()),
)
// Payments a label can be merged into: everything classified but ignored
const mergeTargets = computed(() => payments.value.filter((p) => p.kind !== 'dismissed'))

function candidateId(c: RecurringCandidate): string {
  return `${c.key}-${c.amount}`
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [ov, cands, grps] = await Promise.all([
      getRecurringOverview(),
      listRecurringCandidates(),
      listCategoryGroups(),
    ])
    overview.value = ov
    candidates.value = cands
    groups.value = grps
  } catch {
    // Errors are shown by the client interceptor
  } finally {
    loading.value = false
  }
}

async function run(action: () => Promise<RecurringOverview | void>): Promise<void> {
  busy.value = true
  try {
    const result = await action()
    if (result) overview.value = result
    candidates.value = await listRecurringCandidates()
  } catch {
    // Errors are shown by the client interceptor
  } finally {
    busy.value = false
  }
}

function classify(candidate: RecurringCandidate, kind: RecurringKind): Promise<void> {
  return run(() => classifyRecurring(candidate, kind, defaultName(candidate.key)))
}

function update(payment: RecurringPayment, payload: RecurringUpdate): Promise<void> {
  return run(() => updateRecurring(payment.id, payload))
}

function forget(payment: RecurringPayment): Promise<void> {
  return run(() => forgetRecurring(payment.id))
}

function attach(candidate: RecurringCandidate, paymentId: number): Promise<void> {
  mergingCandidate.value = null
  return run(() => attachRecurring(paymentId, candidate))
}

function merge(payment: RecurringPayment, otherId: number): Promise<void> {
  mergingPaymentId.value = null
  return run(() => mergeRecurring(payment.id, otherId))
}

function acceptPrice(payment: RecurringPayment): Promise<void> {
  return run(() => acceptRecurringPrice(payment.id))
}

function detach(payment: RecurringPayment, aliasId: number): Promise<void> {
  return run(() => detachRecurring(payment.id, aliasId))
}

function othersThan(payment: RecurringPayment): RecurringPayment[] {
  return mergeTargets.value.filter((p) => p.id !== payment.id)
}

function startRename(payment: RecurringPayment): void {
  renamingId.value = payment.id
  renameValue.value = payment.name
}

async function saveRename(payment: RecurringPayment): Promise<void> {
  const name = renameValue.value.trim()
  renamingId.value = null
  if (name && name !== payment.name) await update(payment, { name })
}

function startCancel(payment: RecurringPayment): void {
  cancellingId.value = payment.id
  cancelDate.value = localToday()
}

async function confirmCancel(payment: RecurringPayment): Promise<void> {
  const date = cancelDate.value
  cancellingId.value = null
  if (date) await update(payment, { cancelled_at: date })
}

function onCategoryChange(payment: RecurringPayment, event: Event): void {
  const value = (event.target as HTMLSelectElement).value
  void update(payment, { category_id: value ? Number(value) : null })
}

function attentionText(payment: RecurringPayment): string[] {
  const lines: string[] = []
  if (payment.debits_after_cancellation.length > 0) {
    const dates = payment.debits_after_cancellation.map(formatDay).join(', ')
    lines.push(`Encore prélevé après la résiliation : ${dates}`)
  }
  if (payment.price_changed && payment.status !== 'cancelled') {
    lines.push(
      `Prix passé de ${formatAmount(payment.amount)} à ${formatAmount(payment.current_amount)}`,
    )
  }
  if (payment.status === 'probably_ended' && payment.last_date) {
    lines.push(`Plus prélevé depuis le ${formatDay(payment.last_date)} : terminé ?`)
  }
  return lines
}

onMounted(load)
</script>

<template>
  <div class="px-4 py-5 lg:px-8 lg:py-6 max-w-4xl mx-auto pb-24">
    <h1 class="text-xl font-bold mb-4">Abonnements</h1>

    <div v-if="loading" class="flex flex-col gap-3">
      <div v-for="i in 3" :key="i" class="skeleton h-20 rounded-2xl" />
    </div>

    <template v-else>
      <!-- Totals -->
      <div class="card bg-base-100 border border-base-300 mb-6">
        <div class="card-body p-4 flex-row items-center gap-4">
          <span class="text-3xl">🔁</span>
          <div class="flex-1">
            <p class="text-2xl font-bold tabular-nums" data-test="monthly-total">
              {{ formatAmount(overview?.monthly_total ?? 0) }}<span class="text-sm font-normal text-base-content/50"> / mois</span>
            </p>
            <p class="text-sm text-base-content/60 tabular-nums">
              soit {{ formatAmount(overview?.yearly_total ?? 0) }} par an ·
              {{ activeCount }} abonnement{{ activeCount > 1 ? 's' : '' }} actif{{ activeCount > 1 ? 's' : '' }}
            </p>
          </div>
        </div>
      </div>

      <!-- Nothing found -->
      <div v-if="nothingYet" class="text-center py-12 text-base-content/50">
        <p class="text-5xl mb-4">🔍</p>
        <p class="font-medium">Aucun paiement récurrent trouvé</p>
        <p class="text-sm mt-1">
          Importe tes relevés bancaires : il faut au moins trois prélèvements réguliers
          (deux pour un abonnement annuel) pour en repérer un.
        </p>
      </div>

      <!-- Needs a look -->
      <section v-if="toCheck.length > 0" class="mb-6">
        <h2 class="font-semibold mb-2">⚠️ À vérifier</h2>
        <div class="flex flex-col gap-2">
          <div
            v-for="p in toCheck"
            :key="p.id"
            class="rounded-xl border border-warning bg-warning/10 p-3"
          >
            <div class="flex items-center gap-2">
              <span class="font-medium flex-1">{{ p.name }}</span>
              <span class="text-sm tabular-nums">{{ formatAmount(p.current_amount) }} · {{ periodLabel(p.period) }}</span>
            </div>
            <p v-for="line in attentionText(p)" :key="line" class="text-sm mt-1">{{ line }}</p>
            <RecurringLabels :payment="p" :busy="busy" @detach="(id) => detach(p, id)" />
            <div class="flex flex-wrap gap-2 mt-2">
              <button
                v-if="p.price_changed"
                class="btn btn-xs"
                :disabled="busy"
                @click="acceptPrice(p)"
              >Accepter le nouveau prix</button>
              <button
                v-if="p.status === 'probably_ended'"
                class="btn btn-xs"
                :disabled="busy"
                @click="startCancel(p)"
              >Marquer résilié</button>
              <button
                v-if="p.cancelled_at"
                class="btn btn-xs btn-ghost"
                :disabled="busy"
                @click="update(p, { cancelled_at: null })"
              >Annuler la résiliation</button>
              <button
                v-if="othersThan(p).length > 0"
                class="btn btn-xs btn-ghost"
                :disabled="busy"
                @click="mergingPaymentId = p.id"
              >Fusionner avec…</button>
            </div>
            <RecurringPicker
              v-if="mergingPaymentId === p.id"
              :payments="othersThan(p)"
              :prompt="`${p.name} absorbe :`"
              :busy="busy"
              @choose="(id) => merge(p, id)"
              @cancel="mergingPaymentId = null"
            />
            <div v-if="cancellingId === p.id" class="flex items-center gap-2 mt-2">
              <input v-model="cancelDate" type="date" class="input input-xs input-bordered" />
              <button class="btn btn-xs btn-primary" :disabled="busy" @click="confirmCancel(p)">Confirmer</button>
              <button class="btn btn-xs btn-ghost" @click="cancellingId = null">Annuler</button>
            </div>
          </div>
        </div>
      </section>

      <!-- Active subscriptions -->
      <section v-if="active.length > 0" class="mb-6">
        <h2 class="font-semibold mb-2">Mes abonnements</h2>
        <div class="flex flex-col divide-y divide-base-300 rounded-xl border border-base-300 bg-base-100">
          <div v-for="p in active" :key="p.id" class="p-3 flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <input
                v-if="renamingId === p.id"
                v-model="renameValue"
                class="input input-sm input-bordered flex-1"
                maxlength="200"
                @keydown.enter="saveRename(p)"
                @blur="saveRename(p)"
              />
              <button
                v-else
                class="font-medium flex-1 text-left"
                title="Renommer"
                @click="startRename(p)"
              >{{ p.name }} <span class="text-base-content/30 text-xs">✏️</span></button>
              <span class="tabular-nums font-semibold">{{ formatAmount(p.monthly_cost) }}<span class="text-xs font-normal text-base-content/50">/mois</span></span>
            </div>
            <p class="text-xs text-base-content/60">
              {{ formatAmount(p.current_amount) }} · {{ periodLabel(p.period) }}
              <template v-if="p.last_date"> · dernier prélèvement le {{ formatDay(p.last_date) }}</template>
            </p>
            <RecurringLabels :payment="p" :busy="busy" @detach="(id) => detach(p, id)" />
            <div class="flex flex-wrap items-center gap-2 mt-1">
              <select
                class="select select-xs select-bordered max-w-48"
                :value="p.category_id ?? ''"
                :disabled="busy"
                @change="onCategoryChange(p, $event)"
              >
                <option value="">Sans catégorie</option>
                <optgroup v-for="g in groups" :key="g.id" :label="g.name">
                  <option v-for="c in g.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                </optgroup>
              </select>
              <button class="btn btn-xs" :disabled="busy" @click="startCancel(p)">Résilié…</button>
              <button class="btn btn-xs btn-ghost" :disabled="busy" @click="update(p, { kind: 'other' })">Pas un abonnement</button>
              <button
                v-if="othersThan(p).length > 0"
                class="btn btn-xs btn-ghost"
                :disabled="busy"
                @click="mergingPaymentId = p.id"
              >Fusionner avec…</button>
            </div>
            <RecurringPicker
              v-if="mergingPaymentId === p.id"
              :payments="othersThan(p)"
              :prompt="`${p.name} absorbe :`"
              :busy="busy"
              @choose="(id) => merge(p, id)"
              @cancel="mergingPaymentId = null"
            />
            <div v-if="cancellingId === p.id" class="flex items-center gap-2 mt-1">
              <span class="text-xs">Résilié le</span>
              <input v-model="cancelDate" type="date" class="input input-xs input-bordered" />
              <button class="btn btn-xs btn-primary" :disabled="busy" @click="confirmCancel(p)">Confirmer</button>
              <button class="btn btn-xs btn-ghost" @click="cancellingId = null">Annuler</button>
            </div>
          </div>
        </div>
      </section>

      <!-- Candidates -->
      <section v-if="candidates.length > 0" class="mb-6">
        <div class="flex flex-wrap items-center gap-2 mb-1">
          <h2 class="font-semibold flex-1">À classer</h2>
          <label class="flex items-center gap-2 text-xs">
            Dernier prélèvement
            <select v-model.number="sinceMonths" class="select select-xs select-bordered" data-test="since-filter">
              <option v-for="s in SINCE_CHOICES" :key="s.months" :value="s.months">
                {{ s.months === 0 ? 'tout' : `depuis ${s.label}` }}
              </option>
            </select>
          </label>
        </div>
        <p class="text-xs text-base-content/60 mb-2">
          Paiements qui reviennent à intervalle régulier dans tes relevés. Dis à Budgie ce que c'est.
          Si un libellé a changé, « C'est le même que… » le rattache à un abonnement déjà classé.
        </p>
        <p
          v-if="shownCandidates.hidden > 0"
          class="text-xs text-base-content/60 mb-2"
          data-test="hidden-count"
        >
          {{ shownCandidates.hidden }} proposition{{ shownCandidates.hidden > 1 ? 's' : '' }}
          plus ancienne{{ shownCandidates.hidden > 1 ? 's' : '' }} masquée{{ shownCandidates.hidden > 1 ? 's' : '' }} :
          élargis la période pour {{ shownCandidates.hidden > 1 ? 'les' : 'la' }} voir.
        </p>
        <div class="flex flex-col gap-2">
          <div
            v-for="c in shownCandidates.visible"
            :key="candidateId(c)"
            class="rounded-xl border border-base-300 bg-base-100 p-3"
            data-test="candidate"
          >
            <div class="flex items-center gap-2">
              <span class="font-medium flex-1">{{ defaultName(c.key) }}</span>
              <span class="tabular-nums">{{ formatAmount(c.amount) }} · {{ periodLabel(c.period) }}</span>
            </div>
            <p class="text-xs text-base-content/60 truncate" :title="c.label">
              {{ c.occurrences }} prélèvements, du {{ formatDay(c.first_date) }} au {{ formatDay(c.last_date) }} · {{ c.label }}
            </p>
            <div class="flex flex-wrap gap-2 mt-2">
              <button class="btn btn-xs btn-primary" :disabled="busy" @click="classify(c, 'subscription')">Abonnement</button>
              <button class="btn btn-xs" :disabled="busy" @click="classify(c, 'other')">Autre paiement récurrent</button>
              <button class="btn btn-xs btn-ghost" :disabled="busy" @click="classify(c, 'dismissed')">Ignorer</button>
              <button
                v-if="mergeTargets.length > 0"
                class="btn btn-xs btn-ghost"
                :disabled="busy"
                @click="mergingCandidate = candidateId(c)"
              >C'est le même que…</button>
            </div>
            <RecurringPicker
              v-if="mergingCandidate === candidateId(c)"
              :payments="mergeTargets"
              prompt="Même paiement que :"
              :busy="busy"
              @choose="(id) => attach(c, id)"
              @cancel="mergingCandidate = null"
            />
          </div>
        </div>
      </section>

      <!-- Stopped or cancelled -->
      <details v-if="stopped.length > 0" class="mb-4">
        <summary class="font-semibold cursor-pointer">Résiliés ou terminés ({{ stopped.length }})</summary>
        <div class="flex flex-col gap-1 mt-2">
          <div v-for="p in stopped" :key="p.id" class="text-sm px-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="flex-1">{{ p.name }}</span>
              <span class="text-base-content/60 tabular-nums">{{ formatAmount(p.current_amount) }} · {{ periodLabel(p.period) }}</span>
              <span v-if="p.cancelled_at" class="text-xs text-base-content/50">résilié le {{ formatDay(p.cancelled_at) }}</span>
              <button
                v-if="p.cancelled_at"
                class="btn btn-xs btn-ghost"
                :disabled="busy"
                @click="update(p, { cancelled_at: null })"
              >Annuler la résiliation</button>
              <button
                v-if="othersThan(p).length > 0"
                class="btn btn-xs btn-ghost"
                :disabled="busy"
                @click="mergingPaymentId = p.id"
              >Fusionner avec…</button>
            </div>
            <RecurringLabels :payment="p" :busy="busy" @detach="(id) => detach(p, id)" />
            <RecurringPicker
              v-if="mergingPaymentId === p.id"
              :payments="othersThan(p)"
              :prompt="`${p.name} absorbe :`"
              :busy="busy"
              @choose="(id) => merge(p, id)"
              @cancel="mergingPaymentId = null"
            />
          </div>
        </div>
      </details>

      <!-- Other recurring payments -->
      <details v-if="others.length > 0" class="mb-4">
        <summary class="font-semibold cursor-pointer">Autres paiements récurrents ({{ others.length }})</summary>
        <p class="text-xs text-base-content/60 mt-1">Impôts, épargne, assurances… : hors du total des abonnements.</p>
        <div class="flex flex-col gap-1 mt-2">
          <div v-for="p in others" :key="p.id" class="text-sm px-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="flex-1">{{ p.name }}</span>
              <span class="text-base-content/60 tabular-nums">{{ formatAmount(p.current_amount) }} · {{ periodLabel(p.period) }}</span>
              <button class="btn btn-xs btn-ghost" :disabled="busy" @click="update(p, { kind: 'subscription' })">C'est un abonnement</button>
              <button
                v-if="othersThan(p).length > 0"
                class="btn btn-xs btn-ghost"
                :disabled="busy"
                @click="mergingPaymentId = p.id"
              >Fusionner avec…</button>
            </div>
            <RecurringLabels :payment="p" :busy="busy" @detach="(id) => detach(p, id)" />
            <RecurringPicker
              v-if="mergingPaymentId === p.id"
              :payments="othersThan(p)"
              :prompt="`${p.name} absorbe :`"
              :busy="busy"
              @choose="(id) => merge(p, id)"
              @cancel="mergingPaymentId = null"
            />
          </div>
        </div>
      </details>

      <!-- Ignored -->
      <details v-if="dismissed.length > 0" class="mb-4">
        <summary class="font-semibold cursor-pointer">Ignorés ({{ dismissed.length }})</summary>
        <div class="flex flex-col gap-1 mt-2">
          <div v-for="p in dismissed" :key="p.id" class="flex items-center gap-2 text-sm px-1">
            <span class="flex-1">{{ p.name }}</span>
            <span class="text-base-content/60 tabular-nums">{{ formatAmount(p.amount) }} · {{ periodLabel(p.period) }}</span>
            <button class="btn btn-xs btn-ghost" :disabled="busy" @click="forget(p)">Reproposer</button>
          </div>
        </div>
      </details>
    </template>
  </div>
</template>
