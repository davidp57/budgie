import client from './client'
import type { ImportedTransaction, ImportResult, ParsePreviewResponse } from './types'

/**
 * Parse a bank file and return a preview of transactions (not saved).
 * file_format is sent as a query param, file as multipart.
 */
export async function parseFile(
  file: File,
  format: string,
): Promise<ParsePreviewResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await client.post<ParsePreviewResponse>(
    `/api/imports/parse?file_format=${encodeURIComponent(format)}`,
    form,
    // Let axios set Content-Type: multipart/form-data with boundary automatically.
    // The global client default of application/json would otherwise break multipart.
    { headers: { 'Content-Type': undefined } },
  )
  return data
}

/**
 * Confirm import: persist a list of already-parsed transactions into an account.
 * Sends JSON body (not multipart).
 */
export async function confirmImport(
  accountId: number,
  transactions: ImportedTransaction[],
): Promise<ImportResult> {
  const { data } = await client.post<ImportResult>('/api/imports/confirm', {
    account_id: accountId,
    transactions,
  })
  return data
}
