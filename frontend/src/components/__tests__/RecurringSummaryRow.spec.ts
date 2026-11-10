import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import RecurringSummaryRow from '../RecurringSummaryRow.vue'
import RecurringTagEditor from '../RecurringTagEditor.vue'
import type { RecurringSummaryItem, RecurringTag } from '@/api/types'

const tags: RecurringTag[] = [
  { id: 1, name: 'Loisirs' },
  { id: 2, name: 'Téléphone' },
]

function item(overrides: Partial<RecurringSummaryItem> = {}): RecurringSummaryItem {
  return {
    id: 7,
    name: 'Streaming',
    kind: 'subscription',
    period: 'monthly',
    amount: 1599,
    monthly_cost: 1599,
    category_id: null,
    first_date: '2025-09-05',
    last_date: '2026-02-05',
    occurrences: 6,
    tag_ids: [1],
    debits: [
      { date: '2026-02-05', amount: 1599 },
      { date: '2026-01-05', amount: 1599 },
      { date: '2025-12-05', amount: 1599 },
      { date: '2025-11-05', amount: 1199 },
      { date: '2025-10-05', amount: 1199 },
      { date: '2025-09-05', amount: 1199 },
    ],
    segments: [
      { start: '2025-09-05', end: '2025-11-05', amount: 1199, count: 3 },
      { start: '2025-12-05', end: '2026-02-05', amount: 1599, count: 3 },
    ],
    ...overrides,
  }
}

function mountRow(overrides: Partial<RecurringSummaryItem> = {}) {
  return mount(RecurringSummaryRow, {
    props: { item: item(overrides), tags, usedTagIds: [1], busy: false },
  })
}

describe('RecurringSummaryRow', () => {
  it('shows the name, the monthly cost, since when, and its tags', () => {
    const text = mountRow().text()
    expect(text).toContain('Streaming')
    expect(text).toContain('15,99')
    expect(text).toContain('depuis sept. 2025')
    expect(text).toContain('Loisirs')
    expect(text).not.toContain('Téléphone')
  })

  it('shows the amount per period when it is not monthly', () => {
    const text = mountRow({ period: 'yearly', amount: 12000, monthly_cost: 1000 }).text()
    expect(text).toContain('120,00')
    expect(text).toContain('annuel')
  })

  it('unfolds on its history: prices most recent first, then the debits', async () => {
    const wrapper = mountRow()
    expect(wrapper.find('[data-test=summary-history]').exists()).toBe(false)

    await wrapper.find('[data-test=summary-toggle]').trigger('click')

    const prices = wrapper.findAll('[data-test=summary-price]').map((p) => p.text())
    expect(prices).toHaveLength(2)
    expect(prices[0]).toContain('15,99')
    expect(prices[0]).toContain('depuis déc. 2025')
    expect(prices[1]).toContain('11,99')
    expect(prices[1]).toContain('sept. 2025')
    expect(prices[1]).toContain('nov. 2025')
    const debits = wrapper.findAll('[data-test=summary-debit]')
    expect(debits).toHaveLength(6)
    expect(debits[0]!.text()).toContain('05/02/2026')
    expect(wrapper.findComponent(RecurringTagEditor).exists()).toBe(true)
  })

  it('passes the tag actions on, for this payment', async () => {
    const wrapper = mountRow()
    await wrapper.find('[data-test=summary-toggle]').trigger('click')
    const editor = wrapper.findComponent(RecurringTagEditor)
    editor.vm.$emit('tag', 2)
    editor.vm.$emit('untag', 1)
    editor.vm.$emit('create', 'Famille')
    editor.vm.$emit('delete', 2)
    expect(wrapper.emitted('tag')).toEqual([[7, 2]])
    expect(wrapper.emitted('untag')).toEqual([[7, 1]])
    expect(wrapper.emitted('create')).toEqual([[7, 'Famille']])
    expect(wrapper.emitted('deleteTag')).toEqual([[2]])
  })
})

describe('RecurringTagEditor', () => {
  function mountEditor() {
    return mount(RecurringTagEditor, {
      props: { tags, selected: [1], usedTagIds: [1], busy: false },
    })
  }

  it('toggles a tag on and off', async () => {
    const wrapper = mountEditor()
    const chips = wrapper.findAll('[data-test=tag-toggle]')
    await chips[0]!.trigger('click')
    await chips[1]!.trigger('click')
    expect(wrapper.emitted('untag')).toEqual([[1]])
    expect(wrapper.emitted('tag')).toEqual([[2]])
  })

  it('creates a new tag from its name', async () => {
    const wrapper = mountEditor()
    await wrapper.find('[data-test=tag-new]').setValue('  Famille ')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('create')).toEqual([['Famille']])
    expect((wrapper.find('[data-test=tag-new]').element as HTMLInputElement).value).toBe('')
  })

  it('puts an existing tag on when its name is typed again', async () => {
    const wrapper = mountEditor()
    await wrapper.find('[data-test=tag-new]').setValue('téléphone')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('create')).toBeUndefined()
    expect(wrapper.emitted('tag')).toEqual([[2]])
  })

  it('offers to delete only the tags no payment carries', async () => {
    const wrapper = mountEditor()
    const deletes = wrapper.findAll('[data-test=tag-delete]')
    expect(deletes).toHaveLength(1)
    await deletes[0]!.trigger('click')
    expect(wrapper.emitted('delete')).toEqual([[2]])
  })
})
