import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import SubscriptionsSummaryView from '../SubscriptionsSummaryView.vue'
import RecurringSummaryRow from '@/components/RecurringSummaryRow.vue'
import {
  createRecurringTag,
  getRecurringSummary,
  tagRecurring,
  untagRecurring,
} from '@/api/recurring'
import type { RecurringSummary, RecurringSummaryItem } from '@/api/types'

vi.mock('@/api/recurring', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/recurring')>()
  return {
    ...actual,
    getRecurringSummary: vi.fn(),
    createRecurringTag: vi.fn(),
    deleteRecurringTag: vi.fn(),
    tagRecurring: vi.fn(),
    untagRecurring: vi.fn(),
  }
})

function item(id: number, name: string, monthly: number, tagIds: number[], kind = 'subscription'): RecurringSummaryItem {
  return {
    id,
    name,
    kind: kind as RecurringSummaryItem['kind'],
    period: 'monthly',
    amount: monthly,
    monthly_cost: monthly,
    category_id: null,
    first_date: '2025-01-05',
    last_date: '2026-11-05',
    occurrences: 23,
    tag_ids: tagIds,
    debits: [{ date: '2026-11-05', amount: monthly }],
    segments: [{ start: '2025-01-05', end: '2026-11-05', amount: monthly, count: 23 }],
  }
}

function summary(overrides: Partial<RecurringSummary> = {}): RecurringSummary {
  return {
    as_of: '2026-11-05',
    items: [
      item(1, 'Livret', 5000, [2], 'other'),
      item(2, 'Box', 2999, [1]),
      item(3, 'Mobile', 1999, [1]),
      item(4, 'Streaming', 1399, []),
    ],
    tags: [
      { id: 2, name: 'Épargne' },
      { id: 1, name: 'Téléphone' },
    ],
    subscriptions_monthly: 2999 + 1999 + 1399,
    subscriptions_yearly: (2999 + 1999 + 1399) * 12,
    monthly_total: 5000 + 2999 + 1999 + 1399,
    yearly_total: (5000 + 2999 + 1999 + 1399) * 12,
    to_confirm_count: 2,
    attention_count: 1,
    ...overrides,
  }
}

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/abonnements', name: 'abonnements', component: SubscriptionsSummaryView },
      { path: '/abonnements/gerer', name: 'abonnements-gerer', component: { template: '<div />' } },
    ],
  })
  await router.push('/abonnements')
  const wrapper = mount(SubscriptionsSummaryView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

/** Collapse non-breaking spaces (French amounts) for text matching. */
function text(el: { text(): string }): string {
  return el.text().replace(/\s/g, ' ')
}

describe('SubscriptionsSummaryView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getRecurringSummary).mockResolvedValue(summary())
  })

  it('shows the totals, subscriptions apart, and one row per payment', async () => {
    const { wrapper } = await mountView()
    expect(text(wrapper.find('[data-test=summary-total]'))).toContain('113,97 €')
    expect(text(wrapper.find('[data-test=summary-total]'))).toContain('1 367,64 €')
    expect(text(wrapper.find('[data-test=summary-subscriptions]'))).toContain('63,97 €')
    expect(wrapper.findAllComponents(RecurringSummaryRow)).toHaveLength(4)
  })

  it('filters by tag: each chip shows its subtotal, the total follows', async () => {
    const { wrapper } = await mountView()
    const chips = wrapper.findAll('[data-test=tag-filter]')
    expect(chips.map((c) => text(c))).toEqual(['Épargne · 50,00 €', 'Téléphone · 49,98 €'])

    await chips[1]!.trigger('click')

    expect(wrapper.findAllComponents(RecurringSummaryRow)).toHaveLength(2)
    expect(text(wrapper.find('[data-test=summary-total]'))).toContain('49,98 €')

    await wrapper.find('[data-test=tag-filter-all]').trigger('click')
    expect(wrapper.findAllComponents(RecurringSummaryRow)).toHaveLength(4)
  })

  it('points to "Gérer" for what is left to confirm or to check', async () => {
    const { wrapper, router } = await mountView()
    expect(text(wrapper.find('[data-test=summary-pending]'))).toContain('2 à confirmer')
    expect(text(wrapper.find('[data-test=summary-pending]'))).toContain('1 à vérifier')

    await wrapper.find('[data-test=manage]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('abonnements-gerer')
  })

  it('invites to "Gérer" when nothing is kept yet', async () => {
    vi.mocked(getRecurringSummary).mockResolvedValue(
      summary({ items: [], tags: [], monthly_total: 0, subscriptions_monthly: 0 }),
    )
    const { wrapper } = await mountView()
    expect(wrapper.find('[data-test=summary-empty]').exists()).toBe(true)
  })

  it('puts, takes off and creates tags, then shows the new summary', async () => {
    const after = summary({ to_confirm_count: 0 })
    vi.mocked(tagRecurring).mockResolvedValue(after)
    vi.mocked(untagRecurring).mockResolvedValue(after)
    vi.mocked(createRecurringTag).mockResolvedValue({ id: 9, name: 'Famille' })
    const { wrapper } = await mountView()
    const row = wrapper.findAllComponents(RecurringSummaryRow)[3]!

    row.vm.$emit('tag', 4, 1)
    await flushPromises()
    expect(tagRecurring).toHaveBeenCalledWith(4, 1)
    expect(wrapper.find('[data-test=summary-pending]').text()).not.toContain('confirmer')

    row.vm.$emit('untag', 4, 1)
    await flushPromises()
    expect(untagRecurring).toHaveBeenCalledWith(4, 1)

    row.vm.$emit('create', 4, 'Famille')
    await flushPromises()
    expect(createRecurringTag).toHaveBeenCalledWith('Famille')
    expect(tagRecurring).toHaveBeenLastCalledWith(4, 9)
  })
})
