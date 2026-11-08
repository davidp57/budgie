import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RecurringTimeline from '../RecurringTimeline.vue'
import type { RecurringLine } from '@/api/types'

function line(id: string, name: string, first: string, last: string, amount = 1918): RecurringLine {
  return {
    id,
    ref: { payment_id: null, key: name.toUpperCase(), amount, period: 'monthly' },
    payment: null,
    name,
    key: name.toUpperCase(),
    label: null,
    period: 'monthly',
    amount,
    monthly_cost: amount,
    first_date: first,
    last_date: last,
    running: last >= '2026-10-01',
    likely_other: false,
    segments: [{ start: first, end: last, amount, count: 4 }],
  }
}

const old = line('a', 'Oldname', '2025-01-10', '2025-05-10')
const recent = line('b', 'Newname', '2025-06-10', '2026-11-01')

describe('RecurringTimeline', () => {
  it('sorts the rows by name, so that one service under two labels sits together', () => {
    const lines = [
      line('z', 'Zeta Cloud', '2025-01-10', '2026-11-01'),
      line('t2', 'Tesla Motors Lux', '2024-01-10', '2024-12-10'),
      line('e', 'Électricité', '2025-01-10', '2026-11-01'),
      line('a', 'amazon prime', '2025-01-10', '2026-11-01'),
      line('t1', 'Tesla Lu', '2025-01-10', '2026-11-01'),
    ]
    const wrapper = mount(RecurringTimeline, {
      props: { lines, suggestions: [], today: '2026-11-08', busy: false },
    })
    const names = wrapper
      .findAll('[data-test=timeline-row]')
      .map((r) => r.find('p').text())
    expect(names).toEqual(['amazon prime', 'Électricité', 'Tesla Lu', 'Tesla Motors Lux', 'Zeta Cloud'])
  })

  it('puts the most recent first among lines of the same name', () => {
    const wrapper = mount(RecurringTimeline, {
      props: {
        lines: [line('a', 'Same', '2024-01-10', '2024-06-10'), line('b', 'Same', '2025-01-10', '2026-11-01')],
        suggestions: [],
        today: '2026-11-08',
        busy: false,
      },
    })
    const rows = wrapper.findAll('[data-test=timeline-row]')
    expect(rows[0]!.text()).toContain('mensuel')
    expect(rows[0]!.find('p').text()).toBe('Same')
    expect(rows[0]!.text()).not.toContain('arrêté')
  })

  it('shows a suggestion on the later line and links in order', async () => {
    const wrapper = mount(RecurringTimeline, {
      props: {
        lines: [old, recent],
        suggestions: [{ earlier_id: 'a', later_id: 'b' }],
        today: '2026-11-08',
        busy: false,
      },
    })
    const newRow = wrapper.findAll('[data-test=timeline-row]').find((r) => r.text().includes('Newname'))!
    expect(newRow.text()).toContain('Probablement la suite de « Oldname »')
    const relier = newRow.findAll('button').find((b) => b.text() === 'Relier')!
    await relier.trigger('click')
    expect(wrapper.emitted('link')![0]).toEqual(['a', 'b'])
  })

  it('links by hand with the line that ends first as the earlier one', async () => {
    const wrapper = mount(RecurringTimeline, {
      props: { lines: [old, recent], suggestions: [], today: '2026-11-08', busy: false },
    })
    // Start from the older row ("Relier à…"), pick the recent line
    const oldRow = wrapper.findAll('[data-test=timeline-row]').find((r) => r.find('p').text() === 'Oldname')!
    await oldRow.findAll('button').find((b) => b.text() === 'relier à…')!.trigger('click')
    await oldRow.find('select').setValue('b')
    await oldRow.findAll('button').find((b) => b.text() === 'Confirmer')!.trigger('click')
    expect(wrapper.emitted('link')![0]).toEqual(['a', 'b'])
  })
})
