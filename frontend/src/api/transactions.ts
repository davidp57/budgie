import client from './client'
import type { Transaction, TransactionCreate, TransactionUpdate } from './types'

export async function listTransactions(options?: {
  accountId?: number
  status?: string
  month?: string
  categoryIds?: number[]
  limit?: number
  offset?: number
}): Promise<Transaction[]> {
  const params: Record<string, unknown> = {}
  if (options?.accountId !== undefined) params.account_id = options.accountId
  if (options?.status !== undefined) params.transaction_status = options.status
  if (options?.month !== undefined) params.month = options.month
  if (options?.categoryIds?.length) params.category_ids = options.categoryIds
  if (options?.limit !== undefined) params.limit = options.limit
  if (options?.offset !== undefined) params.offset = options.offset
  const { data } = await client.get<Transaction[]>('/api/transactions', { params })
  return data
}

export async function listPlannedUnlinked(): Promise<Transaction[]> {
  const { data } = await client.get<Transaction[]>('/api/transactions/planned/unlinked')
  return data
}

export async function linkPlanned(
  realTransactionId: number,
  plannedTransactionId: number,
): Promise<Transaction> {
  const { data } = await client.post<Transaction>('/api/transactions/planned/match', {
    real_transaction_id: realTransactionId,
    planned_transaction_id: plannedTransactionId,
  })
  return data
}

export async function createTransaction(payload: TransactionCreate): Promise<Transaction> {
  const { data } = await client.post<Transaction>('/api/transactions', payload)
  return data
}

export async function updateTransaction(
  id: number,
  payload: TransactionUpdate,
): Promise<Transaction> {
  const { data } = await client.patch<Transaction>(`/api/transactions/${id}`, payload)
  return data
}

export async function deleteTransaction(id: number): Promise<void> {
  await client.delete(`/api/transactions/${id}`)
}
