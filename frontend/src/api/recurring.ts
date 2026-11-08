import client from './client'
import type {
  RecurringCandidate,
  RecurringKind,
  RecurringOverview,
  RecurringPayment,
  RecurringPeriod,
} from './types'

/** Recurring debits found in the imported transactions, not classified yet. */
export async function listRecurringCandidates(): Promise<RecurringCandidate[]> {
  const { data } = await client.get<RecurringCandidate[]>('/api/recurring/candidates')
  return data
}

/** Classified payments and the cost of the active subscriptions. */
export async function getRecurringOverview(): Promise<RecurringOverview> {
  const { data } = await client.get<RecurringOverview>('/api/recurring')
  return data
}

/** Record the user's verdict on a candidate. */
export async function classifyRecurring(
  candidate: RecurringCandidate,
  kind: RecurringKind,
  name: string,
): Promise<RecurringOverview> {
  const { data } = await client.post<RecurringOverview>('/api/recurring', {
    key: candidate.key,
    name,
    amount: candidate.amount,
    period: candidate.period,
    kind,
  })
  return data
}

export type RecurringUpdate = Partial<
  Pick<RecurringPayment, 'name' | 'kind' | 'amount' | 'category_id' | 'cancelled_at'>
>

/** Rename, reclassify, categorize, cancel or accept a new price. */
export async function updateRecurring(
  id: number,
  payload: RecurringUpdate,
): Promise<RecurringOverview> {
  const { data } = await client.patch<RecurringOverview>(`/api/recurring/${id}`, payload)
  return data
}

/** Forget a classification: its debits become a candidate again. */
export async function forgetRecurring(id: number): Promise<void> {
  await client.delete(`/api/recurring/${id}`)
}

const PERIOD_LABELS: Record<RecurringPeriod, string> = {
  monthly: 'mensuel',
  quarterly: 'trimestriel',
  yearly: 'annuel',
}

/** French label of a billing rhythm ("mensuel", "trimestriel", "annuel"). */
export function periodLabel(period: RecurringPeriod): string {
  return PERIOD_LABELS[period]
}

/**
 * Readable default name for a candidate: its normalized key in title case
 * ("STREAMFLIX COM" → "Streamflix Com").
 */
export function defaultName(key: string): string {
  return key
    .toLowerCase()
    .split(' ')
    .map((w) => (w ? w[0]!.toUpperCase() + w.slice(1) : w))
    .join(' ')
}

/**
 * True when a subscription needs a look: stopped, debited after cancellation,
 * or new price. Mirrors the server's `attention_count`; a price change on a
 * cancelled subscription no longer matters.
 */
export function needsAttention(payment: RecurringPayment): boolean {
  if (payment.kind !== 'subscription') return false
  if (payment.status === 'cancelled') return payment.debits_after_cancellation.length > 0
  return payment.status === 'probably_ended' || payment.price_changed
}

/** Today's date in the browser's time zone, as YYYY-MM-DD. */
export function localToday(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

/** Format an ISO date (YYYY-MM-DD) as a short French date ("05/02/2026"). */
export function formatDay(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}
