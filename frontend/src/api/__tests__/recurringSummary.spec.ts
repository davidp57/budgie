import { beforeEach, describe, expect, it, vi } from 'vitest'
import client from '../client'
import {
  createRecurringTag,
  deleteRecurringTag,
  filterByTags,
  getRecurringSummary,
  sinceLabel,
  summaryTotals,
  tagRecurring,
  tagSubtotals,
  untagRecurring,
} from '../recurring'
import type { RecurringSummaryItem, RecurringTag } from '../types'

vi.mock('../client', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

function item(overrides: Partial<RecurringSummaryItem> = {}): RecurringSummaryItem {
  return {
    id: 1,
    name: 'Streaming',
    kind: 'subscription',
    period: 'monthly',
    amount: 1399,
    monthly_cost: 1399,
    category_id: null,
    first_date: '2025-01-05',
    last_date: '2026-11-05',
    occurrences: 23,
    tag_ids: [],
    debits: [],
    segments: [],
    ...overrides,
  }
}

const phone: RecurringTag = { id: 1, name: 'Téléphone' }
const savings: RecurringTag = { id: 2, name: 'Épargne' }
const unused: RecurringTag = { id: 3, name: 'Vide' }

const mobile = item({ id: 10, name: 'Mobile', monthly_cost: 1999, tag_ids: [1] })
const box = item({ id: 11, name: 'Box', monthly_cost: 2999, tag_ids: [1] })
const saving = item({
  id: 12,
  name: 'Livret',
  kind: 'other',
  monthly_cost: 5000,
  tag_ids: [2],
})
const stream = item({ id: 13, name: 'Streaming', monthly_cost: 1399, tag_ids: [] })
const all = [mobile, box, saving, stream]

describe('presentation helpers', () => {
  it('keeps every item when no tag is selected', () => {
    expect(filterByTags(all, [])).toEqual(all)
  })

  it('keeps the items carrying any selected tag', () => {
    expect(filterByTags(all, [1]).map((i) => i.name)).toEqual(['Mobile', 'Box'])
    expect(filterByTags(all, [1, 2]).map((i) => i.name)).toEqual(['Mobile', 'Box', 'Livret'])
  })

  it('totals subscriptions apart from the general total', () => {
    expect(summaryTotals(all)).toEqual({
      subscriptionsMonthly: 1999 + 2999 + 1399,
      subscriptionsYearly: (1999 + 2999 + 1399) * 12,
      monthly: 1999 + 2999 + 5000 + 1399,
      yearly: (1999 + 2999 + 5000 + 1399) * 12,
    })
    expect(summaryTotals(filterByTags(all, [2]))).toEqual({
      subscriptionsMonthly: 0,
      subscriptionsYearly: 0,
      monthly: 5000,
      yearly: 60000,
    })
  })

  it('gives each used tag its monthly subtotal, unused tags left out', () => {
    expect(tagSubtotals(all, [phone, savings, unused])).toEqual([
      { tag: phone, monthly: 1999 + 2999, count: 2 },
      { tag: savings, monthly: 5000, count: 1 },
    ])
  })

  it('says since when a payment runs', () => {
    expect(sinceLabel('2024-02-05')).toBe('depuis févr. 2024')
  })
})

describe('presentation API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('reads the summary', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: { items: [] } })
    expect(await getRecurringSummary()).toEqual({ items: [] })
    expect(client.get).toHaveBeenCalledWith('/api/recurring/summary')
  })

  it('creates a tag', async () => {
    vi.mocked(client.post).mockResolvedValueOnce({ data: phone })
    expect(await createRecurringTag('Téléphone')).toEqual(phone)
    expect(client.post).toHaveBeenCalledWith('/api/recurring/tags', { name: 'Téléphone' })
  })

  it('puts a tag on and takes it off a payment', async () => {
    vi.mocked(client.put).mockResolvedValueOnce({ data: { items: [1] } })
    vi.mocked(client.delete).mockResolvedValueOnce({ data: { items: [2] } })
    expect(await tagRecurring(10, 1)).toEqual({ items: [1] })
    expect(client.put).toHaveBeenCalledWith('/api/recurring/10/tags/1')
    expect(await untagRecurring(10, 1)).toEqual({ items: [2] })
    expect(client.delete).toHaveBeenCalledWith('/api/recurring/10/tags/1')
  })

  it('deletes a tag', async () => {
    vi.mocked(client.delete).mockResolvedValueOnce({ data: { tags: [] } })
    expect(await deleteRecurringTag(3)).toEqual({ tags: [] })
    expect(client.delete).toHaveBeenCalledWith('/api/recurring/tags/3')
  })
})
