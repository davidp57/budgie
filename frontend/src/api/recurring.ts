import client from './client'
import type {
  RecurringBoard,
  RecurringKind,
  RecurringLine,
  RecurringLineRef,
  RecurringPayment,
  RecurringPeriod,
} from './types'

/** Every service line, classified or not, and what runs now. */
export async function getRecurringBoard(): Promise<RecurringBoard> {
  const { data } = await client.get<RecurringBoard>('/api/recurring/board')
  return data
}

/**
 * Classify a line not classified yet (subscription, other, or ignored),
 * optionally declaring it cancelled on a date.
 */
export async function classifyLine(
  line: RecurringLine,
  kind: RecurringKind,
  name: string = line.name,
  cancelledAt: string | null = null,
): Promise<void> {
  await client.post('/api/recurring', {
    key: line.ref.key,
    amount: line.ref.amount,
    period: line.ref.period,
    name,
    kind,
    cancelled_at: cancelledAt,
  })
}

export type RecurringUpdate = Partial<
  Pick<RecurringPayment, 'name' | 'kind' | 'amount' | 'category_id' | 'cancelled_at'>
>

/** Rename, reclassify, categorize or cancel a classified payment. */
export async function updateRecurring(id: number, payload: RecurringUpdate): Promise<void> {
  await client.patch(`/api/recurring/${id}`, payload)
}

/** Take the latest debited amount as the new price of the label that billed it. */
export async function acceptRecurringPrice(id: number): Promise<void> {
  await client.post(`/api/recurring/${id}/accept-price`)
}

/** Detach a merged label: its debits become a line of their own again. */
export async function detachRecurring(id: number, aliasId: number): Promise<void> {
  await client.delete(`/api/recurring/${id}/aliases/${aliasId}`)
}

/** Forget a classification: the line goes back to "detected". */
export async function forgetRecurring(id: number): Promise<void> {
  await client.delete(`/api/recurring/${id}`)
}

/** One service, two labels: the later line absorbs the earlier one. */
export async function linkLines(
  earlier: RecurringLineRef,
  later: RecurringLineRef,
): Promise<RecurringBoard> {
  const { data } = await client.post<RecurringBoard>('/api/recurring/link', { earlier, later })
  return data
}

/** Forget every classification; imported transactions stay. */
export async function resetRecurring(): Promise<RecurringBoard> {
  const { data } = await client.delete<RecurringBoard>('/api/recurring')
  return data
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

/** Readable name of a normalized key ("STREAMFLIX COM" → "Streamflix Com"). */
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

/** Where a line goes on the "now" view. */
export type LineGroup = 'check' | 'subscription' | 'other' | 'stopped' | 'ignored'

/** Sort a line into a group of the "now" view. */
export function lineGroup(line: RecurringLine): LineGroup {
  const p = line.payment
  if (p?.kind === 'dismissed') return 'ignored'
  if (p && needsAttention(p)) return 'check'
  if (!line.running) return 'stopped'
  if (p?.kind === 'other' || (!p && line.likely_other)) return 'other'
  return 'subscription'
}

/**
 * Position of a date on a timeline running from `start` to `end`, in percent.
 * Dates outside the window are clamped to its edges.
 */
export function timelinePercent(date: string, start: string, end: string): number {
  const t = Date.parse(date)
  const s = Date.parse(start)
  const e = Date.parse(end)
  if (e <= s) return 0
  return Math.min(100, Math.max(0, ((t - s) / (e - s)) * 100))
}

/** ISO date `months` months before `today` (YYYY-MM-DD), day clamped to the month's end. */
export function monthsBefore(months: number, today: string): string {
  const [y = 0, m = 1, d = 1] = today.split('-').map(Number)
  const total = y * 12 + (m - 1) - months
  const year = Math.floor(total / 12)
  const month = (total % 12) + 1
  const lastDay = new Date(year, month, 0).getDate()
  const day = Math.min(d, lastDay)
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
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

const MONTHS = [
  'janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin',
  'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.',
]

/** Format an ISO date as a short French month ("févr. 2026"). */
export function formatMonth(iso: string): string {
  const [y = '2000', m = '01'] = iso.split('-')
  return `${MONTHS[Number(m) - 1]} ${y}`
}
