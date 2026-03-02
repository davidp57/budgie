import client from './client'
import type { ImportResult, ParsePreviewResponse } from './types'

/**
 * Upload a bank file for parsing preview.
 * Returns parsed transactions without saving them.
 */
export async function parseFile(
  file: File,
  format: string,
): Promise<ParsePreviewResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('format', format)
  const { data } = await client.post<ParsePreviewResponse>('/api/import/preview', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

/**
 * Confirm import of parsed transactions into an account.
 */
export async function confirmImport(
  accountId: number,
  file: File,
  format: string,
): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('account_id', String(accountId))
  form.append('format', format)
  const { data } = await client.post<ImportResult>('/api/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
