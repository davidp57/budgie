import client from './client'
import type { BudgetLineInput, MonthBudget } from './types'

export async function getMonthBudget(month: string): Promise<MonthBudget> {
  const { data } = await client.get<MonthBudget>(`/api/budget/${month}`)
  return data
}

export async function setMonthBudget(
  month: string,
  lines: BudgetLineInput[],
): Promise<void> {
  await client.put(`/api/budget/${month}`, lines)
}
