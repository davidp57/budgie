import client from './client'
import type { BudgetLineInput, IncomeProposalsResponse, MonthBudget } from './types'

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

export async function getIncomeProposals(
  month: string,
  thresholdCentimes?: number,
): Promise<IncomeProposalsResponse> {
  const params: Record<string, string> = {}
  if (thresholdCentimes !== undefined) {
    params['threshold_centimes'] = String(thresholdCentimes)
  }
  const { data } = await client.get<IncomeProposalsResponse>(
    `/api/budget/${month}/income-proposals`,
    { params },
  )
  return data
}