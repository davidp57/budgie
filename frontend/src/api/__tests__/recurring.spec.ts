import { describe, it, expect } from 'vitest'
import {
  defaultName,
  formatDay,
  formatMonth,
  countsInTotal,
  localToday,
  monthsBefore,
  needsAttention,
  parseFrenchDate,
  periodLabel,
  renameKind,
  timelinePercent,
  timelineSection,
} from '../recurring'
import type { RecurringLine, RecurringPayment } from '../types'

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

function line(overrides: Partial<RecurringLine> = {}): RecurringLine {
  return {
    id: 'sSTREAMFLIX|1399|2026-01-01',
    ref: { payment_id: null, key: 'STREAMFLIX', amount: 1399, period: 'monthly' },
    payment: null,
    name: 'Streamflix',
    key: 'STREAMFLIX',
    label: 'CARTE STREAMFLIX',
    period: 'monthly',
    amount: 1399,
    monthly_cost: 1399,
    first_date: '2026-01-01',
    last_date: '2026-11-01',
    running: true,
    likely_other: false,
    segments: [],
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

  it('formats days and months the French way', () => {
    expect(formatDay('2026-02-05')).toBe('05/02/2026')
    expect(formatMonth('2026-02-05')).toBe('févr. 2026')
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

  it('counts a line in the total the way the server does', () => {
    expect(countsInTotal(line())).toBe(true)
    expect(countsInTotal(line({ likely_other: true }))).toBe(false)
    expect(countsInTotal(line({ running: false }))).toBe(false)
    expect(countsInTotal(line({ payment: payment() }))).toBe(true)
    expect(countsInTotal(line({ payment: payment({ kind: 'other' }) }))).toBe(false)
    expect(countsInTotal(line({ payment: payment({ status: 'cancelled' }) }))).toBe(false)
    expect(countsInTotal(line({ likely_other: true, payment: payment() }))).toBe(true)
  })

  it('places dates on a timeline, clamped to the window', () => {
    expect(timelinePercent('2026-01-01', '2026-01-01', '2026-12-31')).toBe(0)
    expect(timelinePercent('2026-12-31', '2026-01-01', '2026-12-31')).toBe(100)
    expect(timelinePercent('2025-06-01', '2026-01-01', '2026-12-31')).toBe(0)
    expect(Math.round(timelinePercent('2026-07-02', '2026-01-01', '2026-12-31'))).toBe(50)
  })

  it('goes back a number of months, clamped to the end of a short month', () => {
    expect(monthsBefore(24, '2026-11-08')).toBe('2024-11-08')
    expect(monthsBefore(3, '2026-05-31')).toBe('2026-02-28')
  })

  it('renames a detected line without turning "probably not" into a subscription', () => {
    expect(renameKind(line())).toBe('subscription')
    expect(renameKind(line({ likely_other: true }))).toBe('other')
  })

  it('puts each line in a section of the timeline', () => {
    expect(timelineSection(line())).toBe('main')
    expect(timelineSection(line({ running: false }))).toBe('main')
    expect(timelineSection(line({ payment: payment() }))).toBe('main')
    expect(timelineSection(line({ payment: payment({ kind: 'other' }) }))).toBe('other')
    expect(timelineSection(line({ likely_other: true }))).toBe('other')
    // A confirmed subscription stays up, whatever the heuristic says
    expect(timelineSection(line({ likely_other: true, payment: payment() }))).toBe('main')
    expect(timelineSection(line({ payment: payment({ kind: 'dismissed' }) }))).toBe('ignored')
  })

  it('reads a French date, and refuses what is not one', () => {
    expect(parseFrenchDate('15/12/2025')).toBe('2025-12-15')
    expect(parseFrenchDate(' 5/1/2026 ')).toBe('2026-01-05')
    expect(parseFrenchDate('29/02/2024')).toBe('2024-02-29')
    expect(parseFrenchDate('29/02/2025')).toBeNull()
    expect(parseFrenchDate('31/04/2026')).toBeNull()
    expect(parseFrenchDate('2026-02-03')).toBeNull()
    expect(parseFrenchDate('12/31/2025')).toBeNull()
    expect(parseFrenchDate('')).toBeNull()
  })
})
