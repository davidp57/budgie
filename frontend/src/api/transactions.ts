import client from './client'
import type { Transaction, TransactionCreate, TransactionUpdate } from './types'

export async function listTransactions(
  accountId?: number,
  isVirtual?: boolean,
): Promise<Transaction[]> {
  const params: Record<string, unknown> = {}
  if (accountId !== undefined) params.account_id = accountId
  if (isVirtual !== undefined) params.is_virtual = isVirtual
  const { data } = await client.get<Transaction[]>('/api/transactions', { params })
  return data
}

export async function listVirtualUnlinked(): Promise<Transaction[]> {
  const { data } = await client.get<Transaction[]>('/api/transactions/virtual/unlinked')
  return data
}

export async function linkVirtual(
  realTransactionId: number,
  virtualTransactionId: number,
): Promise<Transaction> {
  const { data } = await client.post<Transaction>('/api/transactions/virtual/match', {
    real_transaction_id: realTransactionId,
    virtual_transaction_id: virtualTransactionId,
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
