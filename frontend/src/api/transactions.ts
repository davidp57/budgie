import client from './client'
import type { Transaction, TransactionCreate, TransactionUpdate } from './types'

export async function listTransactions(accountId?: number): Promise<Transaction[]> {
  const params = accountId !== undefined ? { account_id: accountId } : {}
  const { data } = await client.get<Transaction[]>('/api/transactions', { params })
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
