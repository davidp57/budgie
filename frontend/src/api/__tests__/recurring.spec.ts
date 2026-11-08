import { describe, it, expect } from 'vitest'
import {
  defaultName,
  filterSince,
  formatDay,
  localToday,
  needsAttention,
  periodLabel,
  sinceDate,
} from '../recurring'
import type { RecurringCandidate, RecurringPayment } from '../types'

function payment(overrides: Partial<RecurringPayment> = {}): RecurringPayment {
  return {
    id: 1,
    key: 'STREAMFLIX',
    name: 'Streamflix',
    kind: 'subscription',
    period: 'monthly',
    amount: 1399,
    current_amount: 1399,
    monthly_cost: 1399,
    category_id: null,
    cancelled_at: null,
    last_date: '2026-11-01',
    occurrences: 6,
    status: 'active',
    price_changed: false,
    debits_after_cancellation: [],
    aliases: [],
    ...overrides,
  }
}

describe('recurring helpers', () => {
  it('labels each period in French', () => {
    expect(periodLabel('monthly')).toBe('mensuel')
    expect(periodLabel('quarterly')).toBe('trimestriel')
    expect(periodLabel('yearly')).toBe('annuel')
  })

  it('turns a normalized key into a readable name', () => {
    expect(defaultName('STREAMFLIX COM')).toBe('Streamflix Com')
  })

  it('formats an ISO day the French way', () => {
    expect(formatDay('2026-02-05')).toBe('05/02/2026')
  })

  it('flags subscriptions that need a look, and only those', () => {
    expect(needsAttention(payment())).toBe(false)
    expect(needsAttention(payment({ status: 'probably_ended' }))).toBe(true)
    expect(needsAttention(payment({ price_changed: true }))).toBe(true)
    expect(needsAttention(payment({ kind: 'other', price_changed: true }))).toBe(false)
  })

  it('forgets a price change once the subscription is cancelled', () => {
    const cancelled = { status: 'cancelled' as const, cancelled_at: '2026-10-01' }
    expect(needsAttention(payment({ ...cancelled, price_changed: true }))).toBe(false)
    expect(
      needsAttention(payment({ ...cancelled, debits_after_cancellation: ['2026-10-05'] })),
    ).toBe(true)
  })

  it('gives today in local time, not UTC', () => {
    expect(localToday(new Date(2026, 0, 1, 0, 30))).toBe('2026-01-01')
  })

  it('computes the start of a period, clamped to the end of a short month', () => {
    expect(sinceDate(3, '2026-11-08')).toBe('2026-08-08')
    expect(sinceDate(12, '2026-01-15')).toBe('2025-01-15')
    expect(sinceDate(3, '2026-05-31')).toBe('2026-02-28')
    expect(sinceDate(0, '2026-11-08')).toBeNull()
  })

  it('hides candidates last debited before the period, and counts them', () => {
    const candidate = (last_date: string): RecurringCandidate => ({
      key: last_date,
      label: last_date,
      amount: 999,
      period: 'monthly',
      monthly_cost: 999,
      occurrences: 4,
      first_date: '2024-01-01',
      last_date,
    })
    const all = [candidate('2026-11-01'), candidate('2026-08-08'), candidate('2025-12-01')]
    const { visible, hidden } = filterSince(all, 3, '2026-11-08')
    expect(visible.map((c) => c.last_date)).toEqual(['2026-11-01', '2026-08-08'])
    expect(hidden).toBe(1)
    expect(filterSince(all, 0, '2026-11-08').hidden).toBe(0)
  })
})
