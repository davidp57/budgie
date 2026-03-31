import client from './client'
import type {
  ClotureRequest,
  ClotureResponse,
  LinkRequest,
  ReconciliationExpense,
  ReconciliationLink,
  ReconciliationSuggestion,
  ReconciliationView,
} from './types'

export async function getReconciliationView(
  accountId: number,
  month: string,
): Promise<ReconciliationView> {
  const { data } = await client.get<ReconciliationView>('/api/reconciliation/view', {
    params: { account_id: accountId, month },
  })
  return data
}

export async function getReconciliationSuggestions(
  accountId: number,
  month: string,
): Promise<ReconciliationSuggestion[]> {
  const { data } = await client.get<ReconciliationSuggestion[]>(
    '/api/reconciliation/suggestions',
    { params: { account_id: accountId, month } },
  )
  return data
}

export async function createLink(req: LinkRequest): Promise<ReconciliationLink> {
  const { data } = await client.post<ReconciliationLink>('/api/reconciliation/link', req)
  return data
}

export async function deleteLink(bankTxId: number): Promise<void> {
  await client.delete(`/api/reconciliation/link/${bankTxId}`)
}

export async function cloture(req: ClotureRequest): Promise<ClotureResponse> {
  const { data } = await client.post<ClotureResponse>('/api/reconciliation/cloture', req)
  return data
}

// Re-export types for convenience
export type { ReconciliationExpense, ReconciliationView }
