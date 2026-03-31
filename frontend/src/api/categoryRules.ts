import client from './client'
import type { CategoryRule, CategoryRuleCreate } from './types'

export async function listRules(): Promise<CategoryRule[]> {
  const { data } = await client.get<CategoryRule[]>('/api/category-rules')
  return data
}

export async function createRule(payload: CategoryRuleCreate): Promise<CategoryRule> {
  const { data } = await client.post<CategoryRule>('/api/category-rules', payload)
  return data
}

export async function updateRule(
  id: number,
  payload: Partial<CategoryRuleCreate>,
): Promise<CategoryRule> {
  const { data } = await client.put<CategoryRule>(`/api/category-rules/${id}`, payload)
  return data
}

export async function deleteRule(id: number): Promise<void> {
  await client.delete(`/api/category-rules/${id}`)
}
