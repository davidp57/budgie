<script setup lang="ts">
/**
 * DepensesView — Budget expense list.
 *
 * Shows manually-created budget transactions (expenses_only=true, i.e. no bank
 * imports). Features:
 * - Filter by month, envelope, category group
 * - Sort by date / amount / label
 * - Group by envelope / category / category group / none
 * - Edit modal (amount, memo, category, envelope)
 * - Delete with confirmation
 * - Shows linked bank transaction info when reconciled
 */

import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { listGroupsWithCategories } from '@/api/categories'
import { useUnassignedCount } from '@/composables/useUnassignedCount'
import { listEnvelopes } from '@/api/envelopes'
import {
  deleteTransaction,
  listTransactions,
  updateTransaction,
} from '@/api/transactions'
import {
  formatAmount,
  type CategoryGroupWithCategories,
  type CategoryRef,
  type Envelope,
  type Transaction,
  type TransactionUpdate,
} from '@/api/types'
import CategoryPicker from '@/components/CategoryPicker.vue'
import DonutChart from '@/components/DonutChart.vue'

// ── Data ──────────────────────────────────────────────────────────

const route = useRoute()
const allExpenses = ref<Transaction[]>([])
const groups = ref<CategoryGroupWithCategories[]>([])
const envelopes = ref<Envelope[]>([])
const loading = ref(true)
const error = ref('')

// ── Filters ───────────────────────────────────────────────────────

const today = new Date()
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`

const filterMonth = ref(currentMonth)
const filterEnvelopeId = ref<number | null>(null)
const filterGroupId = ref<number | null>(null)
// When true, show only manually-created expenses with no envelope ("hors budget").
// Same definition as the unassigned badge: envelope_id null + not a bank import + not a pointage expense.
const filterUnassigned = ref(false)
const unassigned = useUnassignedCount()

// List of expenses filtered by the current UI filters.
// The dashboard always uses the full allExpenses set.
const expenses = computed<Transaction[]>(() => {
  let result = allExpenses.value
  if (filterUnassigned.value) {
    return result.filter(
      (t) => t.envelope_id === null && t.import_hash === null && t.reconciled_with_id === null,
    )
  }
  if (filterEnvelopeId.value !== null) {
    const targetEnv = envelopes.value.find((e) => e.id === filterEnvelopeId.value)
    result = result.filter((t) => {
      if (t.envelope_id === filterEnvelopeId.value) return true
      if (targetEnv && t.category_id !== null) {
        return (targetEnv.categories as CategoryRef[]).some((c) => c.id === t.category_id)
      }
      return false
    })
  }
  if (filterGroupId.value !== null) {
    result = result.filter((t) => {
      if (t.category_id === null) return false
      const grp = groups.value.find((g) => g.categories.some((c) => c.id === t.category_id))
      return grp?.id === filterGroupId.value
    })
  }
  return result
})

// ── View mode (list / dashboard) ─────────────────────────────────

type ViewMode = 'list' | 'dashboard'
const viewMode = ref<ViewMode>('list')

// ── Sort ─────────────────────────────────────────────────────────

type SortKey = 'date-desc' | 'date-asc' | 'amount-desc' | 'amount-asc' | 'label-asc'
const sortKey = ref<SortKey>('date-desc')

// ── Group by ─────────────────────────────────────────────────────

type GroupBy = 'none' | 'envelope' | 'category' | 'category_group'
const groupBy = ref<GroupBy>('none')

// ── Edit modal ────────────────────────────────────────────────────

const editTxn = ref<Transaction | null>(null)
const editForm = ref({
  date: '',
  amount: '',
  memo: '',
  category_id: null as number | null,
  envelope_id: null as number | null,
})
const editSaving = ref(false)
const deleteConfirm = ref(false)
const editError = ref('')

// ── Load ─────────────────────────────────────────────────────────

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [grps, envs, txns] = await Promise.all([
      listGroupsWithCategories(),
      listEnvelopes(),
      listTransactions({
        expensesOnly: true,
        month: filterMonth.value || undefined,
      }),
    ])
    groups.value = grps
    envelopes.value = envs
    allExpenses.value = txns
  } catch {
    error.value = 'Erreur lors du chargement des dépenses.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // Initialize filters from URL query params
  if (route.query.envelope_id) {
    filterEnvelopeId.value = Number(route.query.envelope_id)
  }
  if (route.query.month) {
    filterMonth.value = String(route.query.month)
  }
  if (route.query.unassigned === 'true') {
    filterUnassigned.value = true
    filterMonth.value = '' // show all months for unassigned view
  }
  await load()
})

// ── Lookup helpers ────────────────────────────────────────────────

function categoryName(id: number | null): string {
  if (id === null) return '—'
  for (const g of groups.value) {
    const cat = g.categories.find((c) => c.id === id)
    if (cat) return cat.name
  }
  return String(id)
}

function envelopeName(id: number | null): string | null {
  if (id === null) return null
  return envelopes.value.find((e) => e.id === id)?.name ?? null
}

function envelopeNameForCategory(categoryId: number | null): string | null {
  if (categoryId === null) return null
  for (const env of envelopes.value) {
    const cats: CategoryRef[] = env.categories
    if (cats.some((c) => c.id === categoryId)) return env.name
  }
  return null
}

function resolvedEnvelopeName(txn: Transaction): string | null {
  return envelopeName(txn.envelope_id) ?? envelopeNameForCategory(txn.category_id)
}

// ── Sort & group computed ─────────────────────────────────────────

const sorted = computed<Transaction[]>(() => {
  const list = [...expenses.value]
  switch (sortKey.value) {
    case 'date-asc':
      return list.sort((a, b) => a.date.localeCompare(b.date))
    case 'amount-desc':
      return list.sort((a, b) => b.amount - a.amount)
    case 'amount-asc':
      return list.sort((a, b) => a.amount - b.amount)
    case 'label-asc':
      return list.sort((a, b) => (a.memo ?? '').localeCompare(b.memo ?? ''))
    default: // date-desc
      return list.sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id)
  }
})

interface Group {
  key: string
  label: string
  total: number
  items: Transaction[]
}

const grouped = computed<Group[]>(() => {
  if (groupBy.value === 'none') {
    const total = sorted.value.reduce((s, t) => s + t.amount, 0)
    return [{ key: 'all', label: '', total, items: sorted.value }]
  }

  const map = new Map<string, Group>()
  for (const txn of sorted.value) {
    let key: string
    let label: string

    if (groupBy.value === 'envelope') {
      const name = resolvedEnvelopeName(txn)
      if (txn.envelope_id != null) {
        key = `env-${txn.envelope_id}`
        label = name ?? 'Sans tiroir'
      } else if (name != null) {
        key = 'uncategorised'
        label = name
      } else {
        key = '__none__'
        label = 'Sans tiroir'
      }
    } else if (groupBy.value === 'category') {
      key = txn.category_id !== null ? String(txn.category_id) : '__none__'
      label = categoryName(txn.category_id)
    } else {
      // category_group
      const grp = txn.category_id
        ? groups.value.find((g) => g.categories.some((c) => c.id === txn.category_id))
        : null
      key = grp ? String(grp.id) : '__none__'
      label = grp?.name ?? 'Sans groupe'
    }

    if (!map.has(key)) {
      map.set(key, { key, label, total: 0, items: [] })
    }
    const g = map.get(key)!
    g.items.push(txn)
    g.total += txn.amount
  }

  return [...map.values()].sort((a, b) => a.label.localeCompare(b.label))
})

const totalAmount = computed(() => expenses.value.reduce((s, t) => s + t.amount, 0))

// ── Formatting helpers ────────────────────────────────────────────

function formatDate(dateStr: string): string {
  const [, m = '01', d = '01'] = dateStr.split('-')
  const months = ['jan', 'fév', 'mar', 'avr', 'mai', 'jun', 'jul', 'aoû', 'sep', 'oct', 'nov', 'déc']
  return `${parseInt(d, 10)} ${months[parseInt(m, 10) - 1]}`
}

// ── Edit modal helpers ────────────────────────────────────────────

function openEdit(txn: Transaction): void {
  editTxn.value = txn
  editForm.value = {
    date: txn.date,
    amount: (txn.amount / 100).toFixed(2),
    memo: txn.memo ?? '',
    category_id: txn.category_id,
    envelope_id: txn.envelope_id,
  }
  deleteConfirm.value = false
  editError.value = ''
}

function closeEdit(): void {
  editTxn.value = null
  deleteConfirm.value = false
  editError.value = ''
}

async function saveEdit(): Promise<void> {
  if (!editTxn.value) return
  const raw = parseFloat(editForm.value.amount.replace(',', '.'))
  if (isNaN(raw)) {
    editError.value = 'Montant invalide.'
    return
  }
  const payload: TransactionUpdate = {
    date: editForm.value.date || undefined,
    amount: Math.round(raw * 100),
    memo: editForm.value.memo.trim() || null,
    category_id: editForm.value.category_id,
    envelope_id: editForm.value.envelope_id,
  }
  editSaving.value = true
  try {
    const updated = await updateTransaction(editTxn.value.id, payload)
    const idx = allExpenses.value.findIndex((t) => t.id === editTxn.value!.id)
    if (idx !== -1) allExpenses.value[idx] = updated
    closeEdit()
    unassigned.refresh()
  } catch {
    editError.value = 'Erreur lors de la sauvegarde.'
  } finally {
    editSaving.value = false
  }
}

async function confirmDelete(): Promise<void> {
  if (!editTxn.value) return
  const id = editTxn.value.id
  editSaving.value = true
  try {
    await deleteTransaction(id)
    allExpenses.value = allExpenses.value.filter((t) => t.id !== id)
    closeEdit()
    unassigned.refresh()
  } catch {
    editError.value = 'Erreur lors de la suppression.'
  } finally {
    editSaving.value = false
  }
}

async function reloadGroups(): Promise<void> {
  groups.value = await listGroupsWithCategories()
}

// ── Month navigation ──────────────────────────────────────────────

function prevMonth(): void {
  const [y, m] = filterMonth.value.split('-').map(Number)
  const d = new Date(y!, m! - 1, 1)
  d.setMonth(d.getMonth() - 1)
  filterMonth.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  load()
}

function nextMonth(): void {
  const [y, m] = filterMonth.value.split('-').map(Number)
  const d = new Date(y!, m! - 1, 1)
  d.setMonth(d.getMonth() + 1)
  filterMonth.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  load()
}

function monthLabel(ym: string): string {
  const [y, m] = ym.split('-').map(Number)
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
  ]
  return `${months[(m ?? 1) - 1]} ${y}`
}

// ── Dashboard data ────────────────────────────────────────────────

// Drill-down selection: which envelope + which category slice was clicked
interface DashboardSelection {
  envelopeKey: string   // 'env-<id>' | '__none__'
  envelopeName: string
  categoryLabel: string // matches the label in the chart
}
const dashboardSelection = ref<DashboardSelection | null>(null)

function onSliceClick(
  envelopeKey: string,
  envelopeName: string,
  payload: { label: string; index: number },
): void {
  // Toggle: clicking the same slice again clears the selection
  if (
    dashboardSelection.value?.envelopeKey === envelopeKey &&
    dashboardSelection.value?.categoryLabel === payload.label
  ) {
    dashboardSelection.value = null
  } else {
    dashboardSelection.value = { envelopeKey, envelopeName, categoryLabel: payload.label }
  }
}

// Expenses filtered by the clicked donut slice
const sliceFilteredExpenses = computed<Transaction[]>(() => {
  const sel = dashboardSelection.value
  if (!sel) return []

  return allExpenses.value.filter((txn) => {
    // Match the envelope
    const envId = txn.envelope_id
    let txnEnvKey: string
    if (envId !== null) {
      txnEnvKey = `env-${envId}`
    } else if (txn.category_id !== null) {
      const matchedEnv = envelopes.value.find((e) =>
        (e.categories as CategoryRef[]).some((c) => c.id === txn.category_id),
      )
      txnEnvKey = matchedEnv ? `env-${matchedEnv.id}` : '__none__'
    } else {
      txnEnvKey = '__none__'
    }
    if (txnEnvKey !== sel.envelopeKey) return false

    // Match the category label
    const catLabel = categoryName(txn.category_id)
    return catLabel === sel.categoryLabel
  })
})

interface EnvelopeChartData {
  envelopeKey: string
  envelopeId: number | null
  name: string
  total: number
  labels: string[]
  data: number[]
}

const dashboardData = computed<EnvelopeChartData[]>(() => {
  // Use ALL expenses for the month (independent of list filters)
  const all = allExpenses.value

  // Build a map: envelopeKey → { meta, categoryTotals }
  const map = new Map<string, {
    envelopeId: number | null
    name: string
    cats: Map<string, number>
    total: number
  }>()

  function ensureEnv(key: string, envId: number | null, name: string): void {
    if (!map.has(key)) {
      map.set(key, { envelopeId: envId, name, cats: new Map(), total: 0 })
    }
  }

  for (const txn of all) {
    // Determine envelope for this transaction
    const envId = txn.envelope_id
    let envKey: string
    let envName: string

    if (envId !== null) {
      const env = envelopes.value.find((e) => e.id === envId)
      envKey = `env-${envId}`
      envName = env ? `${env.emoji} ${env.name}` : `Tiroir #${envId}`
    } else if (txn.category_id !== null) {
      // Find envelope via category membership
      const matchedEnv = envelopes.value.find((e) =>
        (e.categories as CategoryRef[]).some((c) => c.id === txn.category_id),
      )
      if (matchedEnv) {
        envKey = `env-${matchedEnv.id}`
        envName = `${matchedEnv.emoji} ${matchedEnv.name}`
        ensureEnv(envKey, matchedEnv.id, envName)
      } else {
        envKey = '__none__'
        envName = 'Sans tiroir'
      }
    } else {
      envKey = '__none__'
      envName = 'Sans tiroir'
    }

    ensureEnv(envKey, envKey === '__none__' ? null : (envId ?? null), envName)
    const entry = map.get(envKey)!
    entry.total += txn.amount

    // Category label for the slice
    let catLabel = '—'
    if (txn.category_id !== null) {
      for (const g of groups.value) {
        const cat = g.categories.find((c) => c.id === txn.category_id)
        if (cat) { catLabel = cat.name; break }
      }
    }
    entry.cats.set(catLabel, (entry.cats.get(catLabel) ?? 0) + txn.amount)
  }

  // Convert to array, only keep envelopes with actual data
  return [...map.values()]
    .filter((e) => e.total !== 0)
    .sort((a, b) => a.total - b.total) // most negative first
    .map((e): EnvelopeChartData => {
      const labels: string[] = []
      const data: number[] = []
      // Sort categories by absolute amount desc
      const sorted = [...e.cats.entries()].sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
      for (const [label, amount] of sorted) {
        labels.push(label)
        data.push(amount)
      }
      return { envelopeKey: e.envelopeId !== null ? `env-${e.envelopeId}` : '__none__', envelopeId: e.envelopeId, name: e.name, total: e.total, labels, data }
    })
})
</script>

<template>
  <div class="px-4 py-5 lg:px-8 lg:py-6 max-w-5xl mx-auto">

    <!-- ── Header ── -->
    <div class="flex items-center justify-between mb-5 flex-wrap gap-2">
      <h1 class="text-2xl font-bold">Dépenses</h1>
      <div class="flex items-center gap-2 flex-wrap">
        <!-- View mode toggle -->
        <div class="join">
          <button
            class="join-item btn btn-sm"
            :class="viewMode === 'list' ? 'btn-primary' : 'btn-ghost'"
            @click="viewMode = 'list'"
          >
            ☰ Liste
          </button>
          <button
            class="join-item btn btn-sm"
            :class="viewMode === 'dashboard' ? 'btn-primary' : 'btn-ghost'"
            @click="viewMode = 'dashboard'"
          >
            🥧 Dashboard
          </button>
        </div>
        <!-- Month navigation -->
        <div class="flex items-center gap-1">
          <button class="btn btn-ghost btn-sm px-2" @click="prevMonth">‹</button>
          <span class="font-medium text-sm min-w-[130px] text-center">{{ monthLabel(filterMonth) }}</span>
          <button class="btn btn-ghost btn-sm px-2" @click="nextMonth">›</button>
        </div>
      </div>
    </div>

    <!-- ── Filters row (list mode only) ── -->
    <div v-if="viewMode === 'list'" class="flex flex-wrap gap-2 mb-4 items-center">
      <!-- Envelope filter -->
      <select
        v-model="filterEnvelopeId"
        class="select select-bordered select-sm"
        @change="load()"
      >
        <option :value="null">Tous les tiroirs</option>
        <option v-for="env in envelopes" :key="env.id" :value="env.id">
          {{ env.emoji }} {{ env.name }}
        </option>
      </select>

      <!-- Category group filter -->
      <select
        v-model="filterGroupId"
        class="select select-bordered select-sm"
        @change="load()"
      >
        <option :value="null">Tous les groupes</option>
        <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
      </select>

      <!-- Sort -->
      <select v-model="sortKey" class="select select-bordered select-sm">
        <option value="date-desc">Date ↓</option>
        <option value="date-asc">Date ↑</option>
        <option value="amount-desc">Montant ↓</option>
        <option value="amount-asc">Montant ↑</option>
        <option value="label-asc">Libellé A→Z</option>
      </select>

      <!-- Group by -->
      <select v-model="groupBy" class="select select-bordered select-sm">
        <option value="none">Sans groupe</option>
        <option value="envelope">Par tiroir</option>
        <option value="category">Par catégorie</option>
        <option value="category_group">Par groupe</option>
      </select>

      <button class="btn btn-ghost btn-xs ml-auto" @click="load()">
        ↻ Actualiser
      </button>
    </div>

    <!-- ── Error ── -->
    <div v-if="error" class="alert alert-error mb-4 text-sm">{{ error }}</div>

    <!-- ── Loading ── -->
    <div v-if="loading" class="flex flex-col gap-2">
      <div v-for="i in 6" :key="i" class="skeleton h-12 rounded-lg" />
    </div>

    <!-- ══════════ LIST MODE ══════════ -->
    <template v-else-if="viewMode === 'list'">

    <!-- ── Empty ── -->
    <div v-if="expenses.length === 0" class="text-center text-base-content/50 py-16">
      Aucune dépense pour cette période.
    </div>

    <!-- ── Expense list ── -->
    <template v-else>
      <!-- Total bar -->
      <div class="flex justify-between items-center mb-3 px-1 text-sm">
        <span class="text-base-content/60">{{ expenses.length }} dépense{{ expenses.length > 1 ? 's' : '' }}</span>
        <span
          class="font-semibold tabular-nums"
          :class="totalAmount < 0 ? 'text-error' : 'text-success'"
        >
          Total : {{ formatAmount(totalAmount) }}
        </span>
      </div>

      <!-- Groups -->
      <div v-for="grp in grouped" :key="grp.key" class="mb-4">
        <!-- Group header (when groupBy != none) -->
        <div
          v-if="groupBy !== 'none'"
          class="flex justify-between items-center px-3 py-1 bg-base-200 rounded-t text-xs font-semibold text-base-content/70 uppercase tracking-wide"
        >
          <span>{{ grp.label }}</span>
          <span :class="grp.total < 0 ? 'text-error' : 'text-success'">
            {{ formatAmount(grp.total) }}
          </span>
        </div>

        <!-- Rows -->
        <div
          class="card bg-base-100 shadow overflow-hidden"
          :class="groupBy !== 'none' ? 'rounded-t-none' : ''"
        >
          <table class="table table-sm">
            <thead>
              <tr class="text-xs text-base-content/50">
                <th class="w-16">Date</th>
                <th>Libellé</th>
                <th class="hidden md:table-cell">Cat. / Tiroir</th>
                <th class="hidden lg:table-cell text-center">Pointé</th>
                <th class="text-right">Montant</th>
                <th class="w-10"></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="txn in grp.items"
                :key="txn.id"
                class="hover cursor-pointer"
                @click="openEdit(txn)"
              >
                <!-- Date -->
                <td class="text-xs tabular-nums text-base-content/60 whitespace-nowrap">
                  {{ formatDate(txn.date) }}
                </td>

                <!-- Memo -->
                <td>
                  <span class="text-sm">{{ txn.memo ?? '—' }}</span>
                  <!-- Reconciled bank tx info -->
                  <div
                    v-if="txn.linked_transaction"
                    class="text-xs text-base-content/50 mt-0.5"
                  >
                    🏦 {{ txn.linked_transaction.memo ?? '(sans libellé)' }}
                    · {{ formatAmount(txn.linked_transaction.amount) }}
                  </div>
                </td>

                <!-- Category / Envelope (hidden on mobile) -->
                <td class="hidden md:table-cell">
                  <span class="text-sm">{{ categoryName(txn.category_id) }}</span>
                  <div
                    v-if="resolvedEnvelopeName(txn)"
                    class="text-xs text-base-content/50"
                  >
                    🗂 {{ resolvedEnvelopeName(txn) }}
                  </div>
                </td>

                <!-- Reconciled badge (hidden on mobile/tablet) -->
                <td class="hidden lg:table-cell text-center">
                  <span
                    v-if="txn.reconciled_with_id"
                    class="badge badge-success badge-xs"
                    title="Pointé"
                  >✓</span>
                </td>

                <!-- Amount -->
                <td
                  class="text-right text-sm font-semibold tabular-nums whitespace-nowrap"
                  :class="txn.amount < 0 ? 'text-error' : 'text-success'"
                >
                  {{ formatAmount(txn.amount) }}
                </td>

                <!-- Edit button -->
                <td class="text-right">
                  <button
                    class="btn btn-ghost btn-xs"
                    title="Modifier"
                    @click.stop="openEdit(txn)"
                  >
                    ✏️
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    </template> <!-- end v-else-if="viewMode === 'list'" -->

    <!-- ══════════ DASHBOARD MODE ══════════ -->
    <template v-else-if="viewMode === 'dashboard'">
      <div v-if="expenses.length === 0" class="text-center text-base-content/50 py-16">
        Aucune dépense pour cette période.
      </div>
      <template v-else>
        <!-- Summary bar -->
        <div class="flex justify-between items-center mb-5 px-1 text-sm">
          <span class="text-base-content/60">{{ expenses.length }} dépense{{ expenses.length > 1 ? 's' : '' }}</span>
          <span
            class="font-semibold tabular-nums"
            :class="totalAmount < 0 ? 'text-error' : 'text-success'"
          >
            Total : {{ formatAmount(totalAmount) }}
          </span>
        </div>

        <!-- Donut charts grid — one per envelope -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            v-for="chart in dashboardData"
            :key="chart.envelopeKey"
            class="card bg-base-100 shadow p-4 transition-shadow"
            :class="dashboardSelection?.envelopeKey === chart.envelopeKey ? 'ring-2 ring-primary' : ''"
          >
            <DonutChart
              :title="chart.name"
              :labels="chart.labels"
              :data="chart.data"
              :total="chart.total"
              :active-label="dashboardSelection?.envelopeKey === chart.envelopeKey ? dashboardSelection.categoryLabel : null"
              @slice-click="onSliceClick(chart.envelopeKey, chart.name, $event)"
            />
          </div>
        </div>

        <!-- ── Drill-down panel ── -->
        <transition name="fade">
          <div v-if="dashboardSelection && sliceFilteredExpenses.length > 0" class="mt-6">
            <div class="flex items-center gap-2 mb-3">
              <span class="text-sm font-semibold">
                🗂 {{ dashboardSelection.envelopeName }} — {{ dashboardSelection.categoryLabel }}
              </span>
              <span class="badge badge-neutral badge-sm tabular-nums">
                {{ formatAmount(sliceFilteredExpenses.reduce((s, t) => s + t.amount, 0)) }}
              </span>
              <button
                class="btn btn-ghost btn-xs ml-auto"
                @click="dashboardSelection = null"
              >
                ✕ Fermer
              </button>
            </div>
            <div class="card bg-base-100 shadow overflow-hidden">
              <table class="table table-sm">
                <thead>
                  <tr class="text-xs text-base-content/50">
                    <th class="w-16">Date</th>
                    <th>Libellé</th>
                    <th class="hidden sm:table-cell text-center">Pointé</th>
                    <th class="text-right">Montant</th>
                    <th class="w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="txn in sliceFilteredExpenses"
                    :key="txn.id"
                    class="hover cursor-pointer"
                    @click="openEdit(txn)"
                  >
                    <td class="text-xs tabular-nums text-base-content/60 whitespace-nowrap">
                      {{ formatDate(txn.date) }}
                    </td>
                    <td>
                      <span class="text-sm">{{ txn.memo ?? '—' }}</span>
                      <div v-if="txn.linked_transaction" class="text-xs text-base-content/50 mt-0.5">
                        🏦 {{ txn.linked_transaction.memo ?? '(sans libellé)' }}
                        · {{ formatAmount(txn.linked_transaction.amount) }}
                      </div>
                    </td>
                    <td class="hidden sm:table-cell text-center">
                      <span v-if="txn.reconciled_with_id" class="badge badge-success badge-xs" title="Pointé">✓</span>
                    </td>
                    <td
                      class="text-right text-sm font-semibold tabular-nums whitespace-nowrap"
                      :class="txn.amount < 0 ? 'text-error' : 'text-success'"
                    >
                      {{ formatAmount(txn.amount) }}
                    </td>
                    <td class="text-right">
                      <button class="btn btn-ghost btn-xs" title="Modifier" @click.stop="openEdit(txn)">✏️</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </transition>
      </template>
    </template>

    <!-- ── Edit modal ── -->
    <dialog v-if="editTxn" class="modal modal-open">
      <div class="modal-box max-w-md">
        <h3 class="font-bold text-lg mb-4">✏️ Modifier la dépense</h3>

        <!-- Linked bank tx banner -->
        <div
          v-if="editTxn.linked_transaction"
          class="alert alert-success text-sm mb-4 py-2"
        >
          <span>
            🏦 Pointé sur :
            <strong>{{ editTxn.linked_transaction.memo ?? 'Opération bancaire' }}</strong>
            {{ formatAmount(editTxn.linked_transaction.amount) }}
            ({{ editTxn.linked_transaction.date }})
          </span>
        </div>

        <!-- Date -->
        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Date</span></label>
          <input v-model="editForm.date" type="date" class="input input-bordered input-sm" />
        </div>

        <!-- Amount -->
        <div class="form-control mb-3">
          <label class="label">
            <span class="label-text">Montant (négatif = dépense, ex. -50.00)</span>
          </label>
          <input
            v-model="editForm.amount"
            type="text"
            placeholder="-50.00"
            class="input input-bordered input-sm"
          />
        </div>

        <!-- Memo -->
        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Libellé</span></label>
          <input
            v-model="editForm.memo"
            type="text"
            placeholder="Description de la dépense"
            class="input input-bordered input-sm"
          />
        </div>

        <!-- Category -->
        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Catégorie</span></label>
          <CategoryPicker
            v-model="editForm.category_id"
            :groups="groups"
            @category-created="reloadGroups"
          />
        </div>

        <!-- Envelope -->
        <div class="form-control mb-4">
          <label class="label"><span class="label-text">Tiroir (direct)</span></label>
          <select v-model="editForm.envelope_id" class="select select-bordered select-sm">
            <option :value="null">— Aucun tiroir direct —</option>
            <option v-for="env in envelopes" :key="env.id" :value="env.id">
              {{ env.emoji }} {{ env.name }}
            </option>
          </select>
        </div>

        <!-- Error -->
        <div v-if="editError" class="alert alert-error text-sm mb-3">{{ editError }}</div>

        <!-- Actions -->
        <div class="modal-action flex flex-wrap gap-2">
          <button
            class="btn btn-primary btn-sm"
            :disabled="editSaving"
            @click="saveEdit"
          >
            <span v-if="editSaving" class="loading loading-spinner loading-xs"></span>
            Enregistrer
          </button>

          <button class="btn btn-ghost btn-sm" @click="closeEdit">Annuler</button>

          <div class="ml-auto">
            <button
              v-if="!deleteConfirm"
              class="btn btn-error btn-sm btn-outline"
              @click="deleteConfirm = true"
            >
              🗑 Supprimer
            </button>
            <div v-else class="flex gap-1 items-center">
              <span class="text-xs text-error">Confirmer ?</span>
              <button
                class="btn btn-error btn-xs"
                :disabled="editSaving"
                @click="confirmDelete"
              >
                Oui
              </button>
              <button class="btn btn-ghost btn-xs" @click="deleteConfirm = false">Non</button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-backdrop" @click="closeEdit"></div>
    </dialog>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
