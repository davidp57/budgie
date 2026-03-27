import client from './client'

export interface ResetResult {
  transactions_deleted: number
  rules_deleted: number
}

export async function resetUserData(): Promise<ResetResult> {
  const { data } = await client.delete<ResetResult>('/api/user/reset')
  return data
}
