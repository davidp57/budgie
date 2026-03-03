import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TransactionRow from '../TransactionRow.vue'
import type { CategoryGroupWithCategories, Transaction } from '@/api/types'

vi.mock('@/api/transactions', () => ({
  updateTransaction: vi.fn().mockResolvedValue({}),
}))

// Stub CategoryPicker to avoid rendering its complex internals.
vi.mock('@/components/CategoryPicker.vue', () => ({
  default: {
    name: 'CategoryPickerStub',
    template: '<div data-testid="category-picker-stub"></div>',
    props: ['modelValue', 'groups'],
    emits: ['update:modelValue', 'category-created'],
  },
}))

const baseTxn: Transaction = {
  id: 1,
  account_id: 1,
  date: '2026-01-15',
  payee_id: null,
  category_id: 2,
  amount: -5000,
  memo: 'Grocery run',
  cleared: 'cleared',
  is_virtual: false,
  virtual_linked_id: null,
  import_hash: null,
  created_at: '2026-01-15T00:00:00',
}

const groups: CategoryGroupWithCategories[] = [
  {
    id: 1,
    name: 'Food',
    sort_order: 0,
    categories: [{ id: 2, name: 'Groceries', group_id: 1, sort_order: 0, hidden: false }],
  },
]

describe('TransactionRow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders date and memo', () => {
    const wrapper = mount(TransactionRow, { props: { txn: baseTxn, groups } })
    expect(wrapper.text()).toContain('2026-01-15')
    expect(wrapper.text()).toContain('Grocery run')
  })

  it('shows amount cell in red for negative amounts', () => {
    const wrapper = mount(TransactionRow, { props: { txn: baseTxn, groups } })
    const amountTd = wrapper.findAll('td').find((td) => td.classes('text-error'))
    expect(amountTd).toBeTruthy()
  })

  it('shows amount cell in green for positive amounts', () => {
    const pos = { ...baseTxn, amount: 10000 }
    const wrapper = mount(TransactionRow, { props: { txn: pos, groups } })
    const amountTd = wrapper.findAll('td').find((td) => td.classes('text-success'))
    expect(amountTd).toBeTruthy()
  })

  it('resolves category name from groups', () => {
    const wrapper = mount(TransactionRow, { props: { txn: baseTxn, groups } })
    expect(wrapper.text()).toContain('Groceries')
  })

  it('shows — for null category', () => {
    const nocat = { ...baseTxn, category_id: null }
    const wrapper = mount(TransactionRow, { props: { txn: nocat, groups } })
    expect(wrapper.text()).toContain('—')
  })

  it('shows forecast badge for virtual transactions', () => {
    const virt = { ...baseTxn, is_virtual: true }
    const wrapper = mount(TransactionRow, { props: { txn: virt, groups } })
    expect(wrapper.text()).toContain('forecast')
  })

  it('shows cleared status badge', () => {
    const wrapper = mount(TransactionRow, { props: { txn: baseTxn, groups } })
    expect(wrapper.text()).toContain('cleared')
  })

  it('enters edit mode on category button click', async () => {
    const wrapper = mount(TransactionRow, { props: { txn: baseTxn, groups } })
    await wrapper.find('button.btn-ghost').trigger('click')
    expect(wrapper.find('[data-testid="category-picker-stub"]').exists()).toBe(true)
  })

  it('shows save and cancel buttons while editing', async () => {
    const wrapper = mount(TransactionRow, { props: { txn: baseTxn, groups } })
    await wrapper.find('button.btn-ghost').trigger('click')
    expect(wrapper.find('button.btn-success').exists()).toBe(true)
    expect(wrapper.find('button.btn-ghost').exists()).toBe(true)
  })

  it('emits category-saved after successful save', async () => {
    const wrapper = mount(TransactionRow, { props: { txn: baseTxn, groups } })
    await wrapper.find('button.btn-ghost').trigger('click')
    await wrapper.find('button.btn-success').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('category-saved')).toBeTruthy()
    expect(wrapper.emitted('category-saved')?.[0]).toEqual([baseTxn, 2])
  })

  it('cancels edit and hides picker on cancel click', async () => {
    const wrapper = mount(TransactionRow, { props: { txn: baseTxn, groups } })
    await wrapper.find('button.btn-ghost').trigger('click')
    // Cancel button is btn-ghost inside the edit template
    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === '✕')
    await cancelBtn!.trigger('click')
    expect(wrapper.find('[data-testid="category-picker-stub"]').exists()).toBe(false)
  })

  it('emits error when save API call fails', async () => {
    const { updateTransaction } = await import('@/api/transactions')
    vi.mocked(updateTransaction).mockRejectedValueOnce(new Error('Network error'))
    const wrapper = mount(TransactionRow, { props: { txn: baseTxn, groups } })
    await wrapper.find('button.btn-ghost').trigger('click')
    await wrapper.find('button.btn-success').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('error')).toBeTruthy()
  })
})
