<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAccounts } from '@/api/accounts'
import { getMonthBudget } from '@/api/budget'
import { listTransactions } from '@/api/transactions'
import { formatAmount, type Account, type MonthBudget, type Transaction } from '@/api/types'
import MonthPicker from '@/components/MonthPicker.vue'

const today = new Date()
const currentMonth = ref(
  `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`,
)

const accounts = ref<Account[]>([])
const budget = ref<MonthBudget | null>(null)
const recentTransactions = ref<Transaction[]>([])
const loading = ref(true)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [acc, bud, txns] = await Promise.all([
      listAccounts(),
      getMonthBudget(currentMonth.value),
      listTransactions({ limit: 10 }),
    ])
    accounts.value = acc
    budget.value = bud
    recentTransactions.value = txns
  } catch {
    error.value = 'Failed to load data.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function onMonthChange(month: string): void {
  currentMonth.value = month
  load()
}

function negativeEnvelopes(): number {
  return budget.value?.envelopes.filter((e) => e.available < 0).length ?? 0
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">Dashboard</h1>
      <MonthPicker :model-value="currentMonth" @update:model-value="onMonthChange" />
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else-if="error" class="alert alert-error">{{ error }}</div>

    <template v-else>
      <!-- Alerts -->
      <div v-if="negativeEnvelopes() > 0" class="alert alert-warning mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        {{ negativeEnvelopes() }} envelope{{ negativeEnvelopes() > 1 ? 's' : '' }} in deficit
      </div>

      <!-- Summary cards -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div class="stat bg-base-100 rounded-box shadow">
          <div class="stat-title">To be budgeted</div>
          <div
            class="stat-value text-xl"
            :class="(budget?.to_be_budgeted ?? 0) >= 0 ? 'text-success' : 'text-error'"
          >
            {{ formatAmount(budget?.to_be_budgeted ?? 0) }}
          </div>
        </div>

        <div class="stat bg-base-100 rounded-box shadow">
          <div class="stat-title">Accounts</div>
          <div class="stat-value text-xl">{{ accounts.length }}</div>
          <div class="stat-desc">on-budget: {{ accounts.filter((a) => a.on_budget).length }}</div>
        </div>

        <div class="stat bg-base-100 rounded-box shadow">
          <div class="stat-title">Envelopes</div>
          <div class="stat-value text-xl">{{ budget?.envelopes.length ?? 0 }}</div>
          <div class="stat-desc text-error" v-if="negativeEnvelopes()">
            {{ negativeEnvelopes() }} in deficit
          </div>
        </div>
      </div>

      <!-- Recent transactions -->
      <div class="card bg-base-100 shadow">
        <div class="card-body p-4">
          <h2 class="card-title text-base mb-3">Recent transactions</h2>
          <div v-if="recentTransactions.length === 0" class="text-base-content/50 text-sm">
            No transactions yet.
          </div>
          <table v-else class="table table-sm">
            <thead>
              <tr>
                <th>Date</th>
                <th>Amount</th>
                <th>Memo</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="txn in recentTransactions" :key="txn.id">
                <td>{{ txn.date }}</td>
                <td :class="txn.amount < 0 ? 'text-error' : 'text-success'">
                  {{ formatAmount(txn.amount) }}
                </td>
                <td class="text-base-content/60">{{ txn.memo ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
