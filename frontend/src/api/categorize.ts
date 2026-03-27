import client from './client'

export interface CategorizeSingleResult {
  category_id: number | null
  confidence: 'auto' | 'rule' | 'none'
}

/**
 * Ask the backend to categorize a single transaction using payee auto-category
 * and user-defined category rules.
 */
export async function categorizeSingle(
  payeeName: string | null,
  memo: string | null,
  amount?: number | null,
): Promise<CategorizeSingleResult> {
  const { data } = await client.post<{ results: CategorizeSingleResult[] }>('/api/categorize', {
    transactions: [{ payee_name: payeeName, memo, amount: amount ?? null }],
  })
  return data.results[0] ?? { category_id: null, confidence: 'none' }
}
