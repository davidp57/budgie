<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { listAccounts } from '@/api/accounts'
import { listGroupsWithCategories } from '@/api/categories'
import { createTransaction, deleteTransaction, listTransactions } from '@/api/transactions'
import {
  formatAmount,
  type Account,
  type CategoryGroupWithCategories,
  type Transaction,
  type TransactionCreate,
} from '@/api/types'
import CategoryPicker from '@/components/CategoryPicker.vue'
import SkeletonRow from '@/components/SkeletonRow.vue'
import TransactionRow from '@/components/TransactionRow.vue'

type TypeFilter = 'all' | 'real' | 'planned'

const PAGE_SIZE = 50

const accounts = ref<Account[]>([])
const groups = ref<CategoryGroupWithCategories[]>([])
const transactions = ref<Transaction[]>([])
const selectedAccountId = ref<number | null>(null)
const typeFilter = ref<TypeFilter>('all')
const loading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(false)
const error = ref('')

// ── Responsive layout ─────────────────────────────────────────────
const mql = window.matchMedia('(max-width: 767px)')
const isMobile = ref(mql.matches)
function onMediaChange(e: MediaQueryListEvent): void {
  isMobile.value = e.matches
}
onMounted(() => mql.addEventListener('change', onMediaChange))
onUnmounted(() => mql.removeEventListener('change', onMediaChange))

// New virtual transaction modal
const showVirtualModal = ref(false)
const saving = ref(false)
const virtualForm = ref<{
  account_id: number | null
  date: string
  amount: string
  category_id: number | null
  memo: string
}>({
  account_id: null,
  date: new Date().toISOString().slice(0, 10),
  amount: '',
  category_id: null,
  memo: '',
})

const txnCount = computed(() => transactions.value.length)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const status =
      typeFilter.value === 'all' ? undefined : typeFilter.value
    const [acc, grps, txns] = await Promise.all([
      listAccounts(),
      listGroupsWithCategories(),
      listTransactions({
        accountId: selectedAccountId.value ?? undefined,
        status,
        limit: PAGE_SIZE,
        offset: 0,
      }),
    ])
    accounts.value = acc
    groups.value = grps
    transactions.value = txns
    hasMore.value = txns.length === PAGE_SIZE
  } catch {
    error.value = 'Failed to load transactions.'
  } finally {
    loading.value = false
  }
}

async function loadMore(): Promise<void> {
  loadingMore.value = true
  try {
    const status =
      typeFilter.value === 'all' ? undefined : typeFilter.value
    const txns = await listTransactions({
      accountId: selectedAccountId.value ?? undefined,
      status,
      limit: PAGE_SIZE,
      offset: txnCount.value,
    })
    transactions.value.push(...txns)
    hasMore.value = txns.length === PAGE_SIZE
  } catch {
    error.value = 'Failed to load more transactions.'
  } finally {
    loadingMore.value = false
  }
}

onMounted(load)

async function onAccountFilter(id: number | null): Promise<void> {
  selectedAccountId.value = id
  await load()
}

async function onTypeFilter(t: TypeFilter): Promise<void> {
  typeFilter.value = t
  await load()
}

function onCategorySaved(txn: Transaction, categoryId: number | null): void {
  txn.category_id = categoryId
}

async function reloadGroups(): Promise<void> {
  groups.value = await listGroupsWithCategories()
}

function openVirtualModal(): void {
  virtualForm.value = {
    account_id: selectedAccountId.value ?? accounts.value[0]?.id ?? null,
    date: new Date().toISOString().slice(0, 10),
    amount: '',
    category_id: null,
    memo: '',
  }
  error.value = ''
  showVirtualModal.value = true
}

function closeVirtualModal(): void {
  showVirtualModal.value = false
}

async function saveVirtualTransaction(): Promise<void> {
  if (!virtualForm.value.account_id) {
    error.value = 'Please select an account.'
    return
  }
  const rawAmount = parseFloat(virtualForm.value.amount.replace(',', '.'))
  if (isNaN(rawAmount)) {
    error.value = 'Invalid amount.'
    return
  }
  const amountCentimes = Math.round(rawAmount * 100)

  const payload: TransactionCreate = {
    account_id: virtualForm.value.account_id,
    date: virtualForm.value.date,
    amount: amountCentimes,
    category_id: virtualForm.value.category_id ?? null,
    memo: virtualForm.value.memo.trim() || null,
    status: 'planned',
  }

  saving.value = true
  try {
    await createTransaction(payload)
    closeVirtualModal()
    await load()
  } catch {
    error.value = 'Failed to create forecast transaction.'
  } finally {
    saving.value = false
  }
}

// ── Mobile swipe-to-delete ────────────────────────────────────────

function categoryName(id: number | null): string {
  if (id === null) return '—'
  for (const g of groups.value) {
    const cat = g.categories.find((c) => c.id === id)
    if (cat) return cat.name
  }
  return String(id)
}

const SWIPE_THRESHOLD = 100
const swipeState = ref<{
  txnId: number | null
  startX: number
  offsetX: number
}>({ txnId: null, startX: 0, offsetX: 0 })

function onTouchStart(txnId: number, e: TouchEvent): void {
  swipeState.value = { txnId, startX: e.touches[0].clientX, offsetX: 0 }
}

function onTouchMove(e: TouchEvent): void {
  if (swipeState.value.txnId === null) return
  const dx = e.touches[0].clientX - swipeState.value.startX
  // Only allow left swipe (negative), cap at -160px
  swipeState.value.offsetX = Math.max(-160, Math.min(0, dx))
}

function onTouchEnd(): void {
  if (swipeState.value.txnId === null) return
  if (swipeState.value.offsetX < -SWIPE_THRESHOLD) {
    const id = swipeState.value.txnId
    swipeState.value = { txnId: null, startX: 0, offsetX: 0 }
    swipeDelete(id)
  } else {
    swipeState.value = { txnId: null, startX: 0, offsetX: 0 }
  }
}

const slidingOutId = ref<number | null>(null)

async function swipeDelete(id: number): Promise<void> {
  // Animate slide-out, then optimistic remove
  slidingOutId.value = id
  await new Promise((r) => setTimeout(r, 250))
  transactions.value = transactions.value.filter((t) => t.id !== id)
  slidingOutId.value = null
  // Fire-and-forget API call
  deleteTransaction(id).catch(() => {
    error.value = 'Échec de la suppression.'
    load()
  })
}

function swipeOffset(txnId: number): string {
  return swipeState.value.txnId === txnId
    ? `translateX(${swipeState.value.offsetX}px)`
    : ''
}

function formatDate(dateStr: string): string {
  const [, m, d] = dateStr.split('-')
  const months = ['jan', 'fév', 'mar', 'avr', 'mai', 'jun', 'jul', 'aoû', 'sep', 'oct', 'nov', 'déc']
  return `${parseInt(d, 10)} ${months[parseInt(m, 10) - 1]}`
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">Transactions</h1>
      <button class="btn btn-secondary btn-sm gap-1" @click="openVirtualModal">
        ⏳ New forecast
      </button>
    </div>

    <!-- Account filter tabs -->
    <div class="tabs tabs-boxed mb-4 flex-wrap gap-1">
      <button
        class="tab"
        :class="selectedAccountId === null ? 'tab-active' : ''"
        @click="onAccountFilter(null)"
      >
        All accounts
      </button>
      <button
        v-for="acc in accounts"
        :key="acc.id"
        class="tab"
        :class="selectedAccountId === acc.id ? 'tab-active' : ''"
        @click="onAccountFilter(acc.id)"
      >
        {{ acc.name }}
      </button>
    </div>

    <!-- Type filter -->
    <div class="flex gap-2 mb-4">
      <button
        v-for="(label, key) in ({ all: 'All', real: 'Real', planned: 'Prévues 🔮' } as Record<TypeFilter, string>)"
        :key="key"
        class="btn btn-sm"
        :class="typeFilter === key ? 'btn-primary' : 'btn-ghost'"
        @click="onTypeFilter(key)"
      >
        {{ label }}
      </button>
    </div>

    <div v-if="error" class="alert alert-error mb-4">{{ error }}</div>

    <!-- ── Mobile list with swipe-to-delete ── -->
    <div v-if="isMobile" class="flex flex-col gap-0.5">
      <template v-if="loading">
        <div v-for="i in 6" :key="i" class="skeleton h-16 rounded-lg" />
      </template>

      <template v-else-if="transactions.length === 0">
        <p class="text-center text-base-content/50 py-12">Aucune transaction.</p>
      </template>

      <template v-else>
        <div
          v-for="txn in transactions"
          :key="txn.id"
          class="relative overflow-hidden rounded-lg"
        >
          <!-- Red delete zone behind -->
          <div class="absolute inset-0 bg-error flex items-center justify-end pr-5">
            <span class="text-error-content font-bold text-sm">Supprimer</span>
          </div>

          <!-- Swipeable content -->
          <div
            class="relative bg-base-100 px-4 py-3 flex items-center gap-3 select-none"
            :class="{
              'transition-transform duration-200': swipeState.txnId !== txn.id,
              'transition-all duration-250 -translate-x-full opacity-0': slidingOutId === txn.id,
            }"
            :style="slidingOutId === txn.id ? {} : { transform: swipeOffset(txn.id) }"
            @touchstart="onTouchStart(txn.id, $event)"
            @touchmove="onTouchMove"
            @touchend="onTouchEnd"
          >
            <!-- Status icon + date -->
            <div class="flex flex-col items-center min-w-[48px]">
              <span v-if="txn.status === 'planned'" class="text-xs">⏳</span>
              <span class="text-xs text-base-content/60 tabular-nums">{{ formatDate(txn.date) }}</span>
            </div>

            <!-- Memo + category -->
            <div class="flex-1 min-w-0">
              <p class="text-sm truncate" :class="txn.status === 'planned' ? 'opacity-60' : ''">
                {{ txn.memo ?? '—' }}
              </p>
              <p class="text-xs text-base-content/50 truncate">{{ categoryName(txn.category_id) }}</p>
            </div>

            <!-- Amount -->
            <span
              class="text-sm font-semibold tabular-nums whitespace-nowrap"
              :class="txn.amount < 0 ? 'text-error' : 'text-success'"
            >
              {{ formatAmount(txn.amount) }}
            </span>
          </div>
        </div>

        <!-- Load more button -->
        <button
          v-if="hasMore"
          class="btn btn-ghost btn-sm mt-2 w-full"
          :disabled="loadingMore"
          @click="loadMore"
        >
          <span v-if="loadingMore" class="loading loading-spinner loading-xs"></span>
          <span v-else>Charger plus…</span>
        </button>
      </template>
    </div>

    <!-- ── Desktop table ── -->
    <div v-else class="card bg-base-100 shadow overflow-x-auto">
      <table class="table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Amount</th>
            <th>Memo</th>
            <th>Category</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <SkeletonRow v-if="loading" :rows="6" :cols="5" />

          <template v-else>
            <tr v-if="transactions.length === 0">
              <td colspan="5" class="text-center text-base-content/50 py-8">No transactions.</td>
            </tr>

            <TransactionRow
              v-for="txn in transactions"
              :key="txn.id"
              :txn="txn"
              :groups="groups"
              @category-saved="onCategorySaved"
              @category-created="reloadGroups"
              @error="error = $event"
              @realized="load"
              @deleted="load"
            />
          </template>
        </tbody>
      </table>

      <!-- Load more button -->
      <div v-if="hasMore && !loading" class="p-3 text-center">
        <button
          class="btn btn-ghost btn-sm"
          :disabled="loadingMore"
          @click="loadMore"
        >
          <span v-if="loadingMore" class="loading loading-spinner loading-xs"></span>
          <span v-else>Load more…</span>
        </button>
      </div>
    </div>

    <!-- Virtual transaction creation modal -->
    <dialog v-if="showVirtualModal" class="modal modal-open">
      <div class="modal-box max-w-md">
        <h3 class="font-bold text-lg mb-4">⏳ New forecast transaction</h3>

        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Account</span></label>
          <select v-model="virtualForm.account_id" class="select select-bordered select-sm">
            <option v-for="acc in accounts" :key="acc.id" :value="acc.id">{{ acc.name }}</option>
          </select>
        </div>

        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Estimated date</span></label>
          <input v-model="virtualForm.date" type="date" class="input input-bordered input-sm" />
        </div>

        <div class="form-control mb-3">
          <label class="label">
            <span class="label-text">Amount (negative = expense, e.g. -50.00)</span>
          </label>
          <input
            v-model="virtualForm.amount"
            type="text"
            placeholder="-50.00"
            class="input input-bordered input-sm"
          />
        </div>

        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Category (optional)</span></label>
          <CategoryPicker
            v-model="virtualForm.category_id"
            :groups="groups"
            @category-created="reloadGroups"
          />
        </div>

        <div class="form-control mb-4">
          <label class="label"><span class="label-text">Memo / description</span></label>
          <input
            v-model="virtualForm.memo"
            type="text"
            placeholder="e.g. Monthly gym subscription"
            class="input input-bordered input-sm"
          />
        </div>

        <div v-if="error" class="alert alert-error text-sm mb-3">{{ error }}</div>

        <div class="modal-action">
          <button
            class="btn btn-primary btn-sm"
            :disabled="saving"
            @click="saveVirtualTransaction"
          >
            <span v-if="saving" class="loading loading-spinner loading-xs"></span>
            Save forecast
          </button>
          <button class="btn btn-ghost btn-sm" @click="closeVirtualModal">Cancel</button>
        </div>
      </div>
      <div class="modal-backdrop" @click="closeVirtualModal"></div>
    </dialog>
  </div>
</template>
