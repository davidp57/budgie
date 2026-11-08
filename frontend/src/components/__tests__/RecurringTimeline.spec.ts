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
      props: { lines, suggestions: [], today: '2026-11-08',
        cancelDefault: '2026-11-08',
        groups: [], busy: false },
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
        cancelDefault: '2026-11-08',
        groups: [],
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
        cancelDefault: '2026-11-08',
        groups: [],
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
      props: { lines: [old, recent], suggestions: [], today: '2026-11-08',
        cancelDefault: '2026-11-08',
        groups: [], busy: false },
    })
    // Start from the older row ("Relier à…"), pick the recent line
    const oldRow = wrapper.findAll('[data-test=timeline-row]').find((r) => r.find('p').text() === 'Oldname')!
    await oldRow.findAll('button').find((b) => b.text() === 'relier à…')!.trigger('click')
    await oldRow.find('select').setValue('b')
    await oldRow.findAll('button').find((b) => b.text() === 'Confirmer')!.trigger('click')
    expect(wrapper.emitted('link')![0]).toEqual(['a', 'b'])
  })

  it('passes a line action up with the id of its line', async () => {
    const wrapper = mount(RecurringTimeline, {
      props: {
        lines: [old, recent],
        suggestions: [],
        today: '2026-11-08',
        cancelDefault: '2026-11-08',
        groups: [],
        busy: false,
      },
    })
    const row = wrapper.findAll('[data-test=timeline-row]').find((r) => r.text().includes('Newname'))!
    await row.findAll('[data-test=menu-item]').find((b) => b.text() === '✓ Abonnement')!.trigger('click')
    expect(wrapper.emitted('action')![0]).toEqual(['b', { type: 'kind', kind: 'subscription' }])
  })

  it('folds the lines that are not subscriptions into a section below', async () => {
    const other: RecurringLine = {
      ...line('o', 'Impots', '2025-01-10', '2026-11-01', 25000),
      likely_other: true,
    }
    const ignored: RecurringLine = {
      ...line('i', 'Vieux', '2024-01-10', '2024-06-10'),
      payment: {
        id: 9,
        key: 'VIEUX',
        name: 'Vieux',
        kind: 'dismissed',
        period: 'monthly',
        amount: 1918,
        current_amount: 1918,
        monthly_cost: 1918,
        category_id: null,
        cancelled_at: null,
        last_date: '2024-06-10',
        occurrences: 4,
        status: 'probably_ended',
        price_changed: false,
        debits_after_cancellation: [],
        aliases: [],
      },
    }
    const wrapper = mount(RecurringTimeline, {
      props: {
        lines: [other, recent, ignored, old],
        suggestions: [],
        today: '2026-11-08',
        cancelDefault: '2026-11-08',
        groups: [],
        busy: false,
      },
    })
    const names = () =>
      wrapper.findAll('[data-test=timeline-row]').map((r) => r.find('p').text())
    // Folded by default: only the main section shows its rows
    expect(names()).toEqual(['Newname', 'Oldname'])
    const headers = wrapper.findAll('[data-test=timeline-section]')
    expect(headers.map((h) => h.text().replace(/^[▸▾]/, ''))).toEqual([
      'Pas des abonnements (1)',
      'Ignorées (1)',
    ])
    await headers[0]!.trigger('click')
    expect(names()).toEqual(['Newname', 'Oldname', 'Impots'])
    await headers[1]!.trigger('click')
    expect(names()).toEqual(['Newname', 'Oldname', 'Impots', 'Vieux'])
  })

  it('refuses a suggestion', async () => {
    const wrapper = mount(RecurringTimeline, {
      props: {
        lines: [old, recent],
        suggestions: [{ earlier_id: 'a', later_id: 'b' }],
        today: '2026-11-08',
        cancelDefault: '2026-11-08',
        groups: [],
        busy: false,
      },
    })
    await wrapper.find('[data-test=suggestion-refuse]').trigger('click')
    expect(wrapper.emitted('refuse')![0]).toEqual(['a', 'b'])
  })
})
