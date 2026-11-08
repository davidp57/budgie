import { describe, it, expect } from 'vitest'
import { defaultName, formatDay, localToday, needsAttention, periodLabel } from '../recurring'
import type { RecurringPayment } from '../types'

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
})
