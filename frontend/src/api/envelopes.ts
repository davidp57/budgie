import client from './client'
import type { Envelope, EnvelopeCreate, EnvelopeUpdate } from './types'

/** List all envelopes for the current user. */
export async function listEnvelopes(): Promise<Envelope[]> {
  const { data } = await client.get<Envelope[]>('/api/envelopes')
  return data
}

/** Create a new envelope. */
export async function createEnvelope(payload: EnvelopeCreate): Promise<Envelope> {
  const { data } = await client.post<Envelope>('/api/envelopes', payload)
  return data
}

/** Update an existing envelope. */
export async function updateEnvelope(id: number, payload: EnvelopeUpdate): Promise<Envelope> {
  const { data } = await client.put<Envelope>(`/api/envelopes/${id}`, payload)
  return data
}

/** Delete an envelope (cascades to its allocations). */
export async function deleteEnvelope(id: number): Promise<void> {
  await client.delete(`/api/envelopes/${id}`)
}
