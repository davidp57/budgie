<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAccounts } from '@/api/accounts'
import { listGroupsWithCategories } from '@/api/categories'
import { listTransactions, updateTransaction } from '@/api/transactions'
import { formatAmount, type Account, type CategoryGroupWithCategories, type Transaction } from '@/api/types'
import CategoryPicker from '@/components/CategoryPicker.vue'

const accounts = ref<Account[]>([])
const groups = ref<CategoryGroupWithCategories[]>([])
const transactions = ref<Transaction[]>([])
const selectedAccountId = ref<number | null>(null)
const loading = ref(true)
const error = ref('')

// Inline edit state
const editingId = ref<number | null>(null)
const editCategoryId = ref<number | null>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [acc, grps, txns] = await Promise.all([
      listAccounts(),
      listGroupsWithCategories(),
      listTransactions(selectedAccountId.value ?? undefined),
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

function startEdit(txn: Transaction): void {
  editingId.value = txn.id
  editCategoryId.value = txn.category_id
}

async function saveEdit(txn: Transaction): Promise<void> {
  try {
    await updateTransaction(txn.id, { category_id: editCategoryId.value })
    txn.category_id = editCategoryId.value
  } finally {
    editingId.value = null
  }
}

function categoryName(categoryId: number | null): string {
  if (!categoryId) return '—'
  for (const group of groups.value) {
    const cat = group.categories.find((c) => c.id === categoryId)
    if (cat) return cat.name
  }
  return '?'
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">Transactions</h1>
    </div>

    <!-- Account filter -->
    <div class="flex gap-2 flex-wrap mb-4">
      <button
        class="btn btn-sm"
        :class="selectedAccountId === null ? 'btn-primary' : 'btn-ghost'"
        @click="onAccountFilter(null)"
      >
        All accounts
      </button>
      <button
        v-for="acc in accounts"
        :key="acc.id"
        class="btn btn-sm"
        :class="selectedAccountId === acc.id ? 'btn-primary' : 'btn-ghost'"
        @click="onAccountFilter(acc.id)"
      >
        {{ acc.name }}
      </button>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else-if="error" class="alert alert-error">{{ error }}</div>

    <div v-else class="card bg-base-100 shadow overflow-x-auto">
      <table class="table table-sm">
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
          <tr v-if="transactions.length === 0">
            <td colspan="5" class="text-center text-base-content/50 py-8">No transactions.</td>
          </tr>

          <tr
            v-for="txn in transactions"
            :key="txn.id"
            :class="txn.is_virtual ? 'opacity-60 border-dashed' : ''"
          >
            <td class="tabular-nums">{{ txn.date }}</td>
            <td :class="txn.amount < 0 ? 'text-error' : 'text-success'" class="tabular-nums">
              {{ formatAmount(txn.amount) }}
            </td>
            <td class="text-base-content/70 max-w-xs truncate">{{ txn.memo ?? '—' }}</td>
            <td>
              <!-- Inline category edit -->
              <template v-if="editingId === txn.id">
                <div class="flex gap-1 items-center">
                  <CategoryPicker v-model="editCategoryId" :groups="groups" />
                  <button class="btn btn-xs btn-success" @click="saveEdit(txn)">✓</button>
                  <button class="btn btn-xs btn-ghost" @click="editingId = null">✕</button>
                </div>
              </template>
              <template v-else>
                <button
                  class="btn btn-ghost btn-xs"
                  @click="startEdit(txn)"
                >
                  {{ categoryName(txn.category_id) }}
                </button>
              </template>
            </td>
            <td>
              <span
                class="badge badge-sm"
                :class="{
                  'badge-ghost': txn.cleared === 'uncleared',
                  'badge-info': txn.cleared === 'cleared',
                  'badge-success': txn.cleared === 'reconciled',
                }"
              >
                {{ txn.cleared }}
              </span>
              <span v-if="txn.is_virtual" class="badge badge-sm badge-warning ml-1">virtual</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
