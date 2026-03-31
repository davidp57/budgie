/**
 * useUnassignedCount — Shared reactive count of "Hors budget" expenses.
 *
 * Module-level ref ensures all component instances share the same value.
 * Call refresh() after creating or assigning an unassigned expense.
 */
import { ref } from 'vue'
import { getUnassignedCount } from '@/api/transactions'

const count = ref(0)

export function useUnassignedCount() {
  async function refresh(): Promise<void> {
    try {
      const data = await getUnassignedCount()
      count.value = data.count
    } catch {
      // Fail silently — badge simply stays hidden
    }
  }

  return { count, refresh }
}
