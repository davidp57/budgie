<script setup lang="ts">
/**
 * HomeView — Main screen showing all budget drawer cards.
 * Tap a card → opens QuickExpense bottom sheet.
 */

import { computed, onMounted, ref } from 'vue'
import { useBudgetStore } from '@/stores/budget'
import { listAccounts } from '@/api/accounts'
import DrawerCard from '@/components/DrawerCard.vue'
import QuickExpense from '@/components/QuickExpense.vue'
import type { Account, EnvelopeLine } from '@/api/types'
import { formatAmount } from '@/api/types'

const budgetStore = useBudgetStore()
const selectedDrawer = ref<EnvelopeLine | null>(null)
const defaultAccount = ref<Account | null>(null)

function onDrawerTap(line: EnvelopeLine): void {
  selectedDrawer.value = line
}

function closeExpense(): void {
  selectedDrawer.value = null
  // Reload budget to reflect new transaction
  budgetStore.loadMonth()
}

// Formatted month name in French (e.g. "Mars 2026")
const monthLabel = computed(() => {
  const [y = '2026', m = '01'] = budgetStore.month.split('-')
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
  ]
  return `${months[parseInt(m, 10) - 1]} ${y}`
})

// Total available across all envelopes
const totalAvailable = computed(() =>
  budgetStore.envelopeLines.reduce((sum, l) => sum + l.available, 0),
)

// Navigate months
function prevMonth(): void {
  const [y = 0, m = 0] = budgetStore.month.split('-').map(Number)
  const prev = m === 1 ? `${y - 1}-12` : `${y}-${String(m - 1).padStart(2, '0')}`
  budgetStore.loadMonth(prev)
}

function nextMonth(): void {
  const [y = 0, m = 0] = budgetStore.month.split('-').map(Number)
  const next = m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, '0')}`
  budgetStore.loadMonth(next)
}

onMounted(async () => {
  try {
    const [, accounts] = await Promise.all([
      budgetStore.loadMonth(),
      listAccounts(),
    ])
    defaultAccount.value = accounts.find((a) => a.on_budget) ?? accounts[0] ?? null
  } catch {
    // 401 errors are handled by the client interceptor (redirect to login)
  }
})
</script>

<template>
  <div class="px-4 py-5 lg:px-8 lg:py-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2 lg:hidden">
        <span class="text-2xl">🐦</span>
        <h1 class="text-xl font-bold">Budgie</h1>
      </div>
      <h1 class="hidden lg:block text-xl font-bold">Tiroirs</h1>
      <!-- Month navigator -->
      <div class="flex items-center gap-1">
        <button class="btn btn-ghost btn-xs btn-circle" @click="prevMonth">‹</button>
        <span class="text-sm font-semibold min-w-[100px] text-center">{{ monthLabel }}</span>
        <button class="btn btn-ghost btn-xs btn-circle" @click="nextMonth">›</button>
      </div>
    </div>

    <!-- Summary line -->
    <p class="text-sm text-base-content/50 mb-5">
      {{ budgetStore.envelopeLines.length }} tiroir{{ budgetStore.envelopeLines.length > 1 ? 's' : '' }}
      · disponible {{ formatAmount(totalAvailable) }}
    </p>

    <!-- Loading skeleton -->
    <div v-if="budgetStore.loading" class="flex flex-col gap-4">
      <div v-for="i in 4" :key="i" class="skeleton h-36 rounded-2xl" />
    </div>

    <!-- Empty state -->
    <div
      v-else-if="budgetStore.envelopeLines.length === 0"
      class="text-center py-20 text-base-content/50"
    >
      <p class="text-5xl mb-4">📭</p>
      <p class="font-medium">Aucun tiroir configuré</p>
      <p class="text-sm mt-1">Crée des enveloppes dans les réglages</p>
    </div>

    <!-- Drawer cards grid -->
    <div v-else class="flex flex-col gap-4 lg:grid lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      <DrawerCard
        v-for="line in budgetStore.envelopeLines"
        :key="line.envelope_id"
        :line="line"
        @tap="onDrawerTap"
      />
    </div>
  </div>

  <!-- No account warning -->
  <div v-if="!budgetStore.loading && !defaultAccount" class="px-4">
    <div class="alert alert-warning text-sm">
      <span>Aucun compte bancaire — crée-en un dans les Réglages.</span>
    </div>
  </div>

  <!-- Quick expense bottom sheet -->
  <QuickExpense
    v-if="selectedDrawer && defaultAccount"
    :drawer="selectedDrawer"
    :account-id="defaultAccount.id"
    @close="closeExpense"
  />
</template>
