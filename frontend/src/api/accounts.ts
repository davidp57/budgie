import client from './client'
import type { Account, AccountCreate, AccountUpdate } from './types'

export async function listAccounts(): Promise<Account[]> {
  const { data } = await client.get<Account[]>('/api/accounts')
  return data
}

export async function createAccount(payload: AccountCreate): Promise<Account> {
  const { data } = await client.post<Account>('/api/accounts', payload)
  return data
}

export async function updateAccount(id: number, payload: AccountUpdate): Promise<Account> {
  const { data } = await client.patch<Account>(`/api/accounts/${id}`, payload)
  return data
}

export async function deleteAccount(id: number): Promise<void> {
  await client.delete(`/api/accounts/${id}`)
}
