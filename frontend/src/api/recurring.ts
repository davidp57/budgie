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

/** Merge a candidate's label into a classified payment ("same as…"). */
export async function attachRecurring(
  id: number,
  candidate: RecurringCandidate,
): Promise<RecurringOverview> {
  const { data } = await client.post<RecurringOverview>(`/api/recurring/${id}/aliases`, {
    key: candidate.key,
    amount: candidate.amount,
  })
  return data
}

/** Merge another classified payment into this one, which absorbs its labels. */
export async function mergeRecurring(id: number, otherId: number): Promise<RecurringOverview> {
  const { data } = await client.post<RecurringOverview>(`/api/recurring/${id}/merge`, {
    other_id: otherId,
  })
  return data
}

/** Take the latest debited amount as the new price of the label that billed it. */
export async function acceptRecurringPrice(id: number): Promise<RecurringOverview> {
  const { data } = await client.post<RecurringOverview>(`/api/recurring/${id}/accept-price`)
  return data
}

/** Detach a merged label: its debits become a candidate again. */
export async function detachRecurring(id: number, aliasId: number): Promise<RecurringOverview> {
  const { data } = await client.delete<RecurringOverview>(
    `/api/recurring/${id}/aliases/${aliasId}`,
  )
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

/** Choices of the "last debit" filter of the candidates, in months (0 = all). */
export const SINCE_CHOICES: { months: number; label: string }[] = [
  { months: 3, label: '3 mois' },
  { months: 6, label: '6 mois' },
  { months: 12, label: '1 an' },
  { months: 24, label: '2 ans' },
  { months: 0, label: 'tout' },
]

/**
 * ISO date `months` months before `today` (YYYY-MM-DD), or null for "all".
 * The day is clamped to the end of a shorter month (31 May − 3 months = 28/29 Feb).
 */
export function sinceDate(months: number, today: string): string | null {
  if (months <= 0) return null
  const [y = 0, m = 1, d = 1] = today.split('-').map(Number)
  const total = y * 12 + (m - 1) - months
  const year = Math.floor(total / 12)
  const month = (total % 12) + 1
  const lastDay = new Date(year, month, 0).getDate()
  const day = Math.min(d, lastDay)
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

/** Candidates whose last debit falls within the chosen period, and how many are hidden. */
export function filterSince(
  candidates: RecurringCandidate[],
  months: number,
  today: string,
): { visible: RecurringCandidate[]; hidden: number } {
  const since = sinceDate(months, today)
  const visible = since ? candidates.filter((c) => c.last_date >= since) : candidates
  return { visible, hidden: candidates.length - visible.length }
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
