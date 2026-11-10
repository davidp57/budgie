import client from './client'
import { formatAmount } from './types'
import type {
  RecurringBoard,
  RecurringKind,
  RecurringLine,
  RecurringLineRef,
  RecurringPayment,
  RecurringPeriod,
  RecurringSummary,
  RecurringSummaryItem,
  RecurringTag,
} from './types'

/** Longest tag name the server accepts, in characters. */
export const TAG_NAME_MAX_LENGTH = 40

/** Months in a year, for the yearly totals. */
const MONTHS_PER_YEAR = 12

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

/** Say no to a link suggestion between two lines; it is not made again. */
export async function refuseLink(earlierKey: string, laterKey: string): Promise<RecurringBoard> {
  const { data } = await client.post<RecurringBoard>('/api/recurring/link/refuse', {
    earlier_key: earlierKey,
    later_key: laterKey,
  })
  return data
}

/** Forget every classification; imported transactions stay. */
export async function resetRecurring(): Promise<RecurringBoard> {
  const { data } = await client.delete<RecurringBoard>('/api/recurring')
  return data
}

/** The running payments the user kept, with their history: the presentation page. */
export async function getRecurringSummary(): Promise<RecurringSummary> {
  const { data } = await client.get<RecurringSummary>('/api/recurring/summary')
  return data
}

/** Create a tag, or get the user's tag of that name (case aside). */
export async function createRecurringTag(name: string): Promise<RecurringTag> {
  const { data } = await client.post<RecurringTag>('/api/recurring/tags', { name })
  return data
}

/** Delete a tag; the payments that carried it lose it. */
export async function deleteRecurringTag(tagId: number): Promise<RecurringSummary> {
  const { data } = await client.delete<RecurringSummary>(`/api/recurring/tags/${tagId}`)
  return data
}

/** Put a tag on a payment. */
export async function tagRecurring(paymentId: number, tagId: number): Promise<RecurringSummary> {
  const { data } = await client.put<RecurringSummary>(`/api/recurring/${paymentId}/tags/${tagId}`)
  return data
}

/** Take a tag off a payment. */
export async function untagRecurring(paymentId: number, tagId: number): Promise<RecurringSummary> {
  const { data } = await client.delete<RecurringSummary>(
    `/api/recurring/${paymentId}/tags/${tagId}`,
  )
  return data
}

/** The items carrying any of the selected tags; every item when none is selected. */
export function filterByTags(
  items: RecurringSummaryItem[],
  selected: number[],
): RecurringSummaryItem[] {
  if (selected.length === 0) return items
  return items.filter((i) => i.tag_ids.some((id) => selected.includes(id)))
}

/** Totals of a list of items: the subscriptions apart, and every item. In centimes. */
export interface SummaryTotals {
  subscriptionsMonthly: number
  subscriptionsYearly: number
  monthly: number
  yearly: number
}

/** What a list of items costs per month and per year, subscriptions apart. */
export function summaryTotals(items: RecurringSummaryItem[]): SummaryTotals {
  const monthly = items.reduce((sum, i) => sum + i.monthly_cost, 0)
  const subscriptionsMonthly = items
    .filter((i) => i.kind === 'subscription')
    .reduce((sum, i) => sum + i.monthly_cost, 0)
  return {
    subscriptionsMonthly,
    subscriptionsYearly: subscriptionsMonthly * MONTHS_PER_YEAR,
    monthly,
    yearly: monthly * MONTHS_PER_YEAR,
  }
}

/** A tag with what its payments cost per month. */
export interface TagSubtotal {
  tag: RecurringTag
  monthly: number
  count: number
}

/** Monthly subtotal of each tag carried by at least one item, in the tags' order. */
export function tagSubtotals(items: RecurringSummaryItem[], tags: RecurringTag[]): TagSubtotal[] {
  return tags
    .map((tag) => {
      const tagged = items.filter((i) => i.tag_ids.includes(tag.id))
      return {
        tag,
        monthly: tagged.reduce((sum, i) => sum + i.monthly_cost, 0),
        count: tagged.length,
      }
    })
    .filter((s) => s.count > 0)
}

/**
 * Where the Home card leads: the presentation once a line is kept
 * (classified, not ignored), the timeline to classify lines before that.
 */
export function subscriptionsRoute(board: RecurringBoard): 'abonnements' | 'abonnements-gerer' {
  const kept = board.lines.some((l) => l.payment !== null && l.payment.kind !== 'dismissed')
  return kept ? 'abonnements' : 'abonnements-gerer'
}

/** Since when a payment runs, from its first debit ("depuis févr. 2024"). */
export function sinceLabel(firstDate: string): string {
  return `depuis ${formatMonth(firstDate)}`
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

/** One correction on a service line, from either tab of the page. */
export type LineAction =
  | { type: 'kind'; kind: RecurringKind }
  | { type: 'rename'; name: string }
  | { type: 'cancel'; date: string | null }
  | { type: 'forget' }
  | { type: 'acceptPrice' }
  | { type: 'category'; categoryId: number | null }
  | { type: 'detach'; aliasId: number }

/**
 * How a detected line is classified when it is only renamed: a line that is
 * probably not a subscription (transfer, 100 €/month or more) must not enter
 * the subscriptions total because it got a name.
 */
export function renameKind(line: RecurringLine): RecurringKind {
  return line.likely_other ? 'other' : 'subscription'
}

/** What needs a look on a classified line: stopped, debited after cancellation, new price. */
export function attentionLines(payment: RecurringPayment): string[] {
  const result: string[] = []
  if (payment.debits_after_cancellation.length > 0) {
    const dates = payment.debits_after_cancellation.map(formatDay).join(', ')
    result.push(`Encore prélevé après la résiliation : ${dates}`)
  }
  if (payment.price_changed && payment.status !== 'cancelled') {
    result.push(`Nouveau prix : ${formatAmount(payment.current_amount)}`)
  }
  if (payment.status === 'probably_ended' && payment.last_date) {
    result.push(`Plus prélevé depuis le ${formatDay(payment.last_date)} : terminé ?`)
  }
  return result
}

/** Where a line goes on the timeline: the main list, or a folded section below. */
export type TimelineSection = 'main' | 'other' | 'ignored'

/**
 * Sort a line into a section of the timeline: what is not a subscription
 * (classified so, or probably so and not confirmed) and what was ignored go
 * to folded sections below the main list.
 */
export function timelineSection(line: RecurringLine): TimelineSection {
  const p = line.payment
  if (p?.kind === 'dismissed') return 'ignored'
  if (p?.kind === 'other' || (!p && line.likely_other)) return 'other'
  return 'main'
}

/**
 * True when a line counts in the subscriptions total, as the server counts it:
 * a running line that is a confirmed subscription (not cancelled, not
 * stopped), or detected and not probably something else.
 */
export function countsInTotal(line: RecurringLine): boolean {
  if (!line.running) return false
  const p = line.payment
  if (!p) return !line.likely_other
  return p.kind === 'subscription' && p.status === 'active'
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

/**
 * Read a French date ("15/12/2025", day and month on one or two digits) as
 * an ISO date (YYYY-MM-DD), or null when it is not a date that exists.
 */
export function parseFrenchDate(text: string): string | null {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(text.trim())
  if (!match) return null
  const [day, month, year] = [Number(match[1]), Number(match[2]), Number(match[3])]
  if (month < 1 || month > 12 || day < 1) return null
  const lastDay = new Date(year, month, 0).getDate()
  if (day > lastDay) return null
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
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
