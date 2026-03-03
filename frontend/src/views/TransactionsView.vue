<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAccounts } from '@/api/accounts'
import { listGroupsWithCategories } from '@/api/categories'
import { createTransaction, listTransactions } from '@/api/transactions'
import {
  type Account,
  type CategoryGroupWithCategories,
  type Transaction,
  type TransactionCreate,
} from '@/api/types'
import CategoryPicker from '@/components/CategoryPicker.vue'
import SkeletonRow from '@/components/SkeletonRow.vue'
import TransactionRow from '@/components/TransactionRow.vue'

type TypeFilter = 'all' | 'real' | 'virtual'

const accounts = ref<Account[]>([])
const groups = ref<CategoryGroupWithCategories[]>([])
const transactions = ref<Transaction[]>([])
const selectedAccountId = ref<number | null>(null)
const typeFilter = ref<TypeFilter>('all')
const loading = ref(true)
const error = ref('')

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

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const isVirtual =
      typeFilter.value === 'all' ? undefined : typeFilter.value === 'virtual'
    const [acc, grps, txns] = await Promise.all([
      listAccounts(),
      listGroupsWithCategories(),
      listTransactions(selectedAccountId.value ?? undefined, isVirtual),
    ])
    accounts.value = acc
    groups.value = grps
    transactions.value = txns
  } catch {
    error.value = 'Failed to load transactions.'
  } finally {
    loading.value = false
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
    is_virtual: true,
    cleared: 'uncleared',
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
        v-for="(label, key) in ({ all: 'All', real: 'Real', virtual: 'Forecast ⏳' } as Record<TypeFilter, string>)"
        :key="key"
        class="btn btn-sm"
        :class="typeFilter === key ? 'btn-primary' : 'btn-ghost'"
        @click="onTypeFilter(key)"
      >
        {{ label }}
      </button>
    </div>

    <div v-if="error" class="alert alert-error mb-4">{{ error }}</div>

    <div class="card bg-base-100 shadow overflow-x-auto">
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
            />
          </template>
        </tbody>
      </table>
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
