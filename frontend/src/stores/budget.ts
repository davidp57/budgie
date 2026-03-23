/**
 * Budget Pinia store — loads monthly budget data (envelope lines).
 */

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getMonthBudget } from '@/api/budget'
import type { MonthBudget, EnvelopeLine } from '@/api/types'

function currentMonth(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

export const useBudgetStore = defineStore('budget', () => {
  const month = ref(currentMonth())
  const budget = ref<MonthBudget | null>(null)
  const loading = ref(false)

  const envelopeLines = computed<EnvelopeLine[]>(() => budget.value?.envelopes ?? [])

  async function loadMonth(m?: string): Promise<void> {
    if (m) month.value = m
    loading.value = true
    try {
      budget.value = await getMonthBudget(month.value)
    } finally {
      loading.value = false
    }
  }

  return { month, budget, loading, envelopeLines, loadMonth }
})
