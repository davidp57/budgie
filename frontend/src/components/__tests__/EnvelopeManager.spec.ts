import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import EnvelopeManager from '../EnvelopeManager.vue'
import type { Envelope } from '@/api/types'

vi.mock('@/api/envelopes', () => ({
  listEnvelopes: vi.fn(),
  createEnvelope: vi.fn(),
  updateEnvelope: vi.fn(),
  deleteEnvelope: vi.fn(),
}))

const sampleEnvelopes: Envelope[] = [
  {
    id: 1,
    name: 'Food',
    emoji: '🍞',
    color_index: null,
    rollover: false,
    sort_order: 0,
    envelope_type: 'regular',
    period: 'monthly',
    target_amount: null,
    stop_on_target: false,
    categories: [{ id: 1, name: 'Groceries', group_name: 'Daily' }],
  },
  {
    id: 2,
    name: 'Transport',
    emoji: '🚗',
    color_index: null,
    rollover: true,
    sort_order: 1,
    envelope_type: 'regular',
    period: 'monthly',
    target_amount: null,
    stop_on_target: false,
    categories: [],
  },
]

describe('EnvelopeManager', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    const { listEnvelopes } = await import('@/api/envelopes')
    vi.mocked(listEnvelopes).mockResolvedValue(sampleEnvelopes)
  })

  it('lists envelopes on mount', async () => {
    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Food')
    expect(wrapper.text()).toContain('Transport')
  })

  it('shows category chips in collapsed view', async () => {
    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Groceries')
  })

  it('shows rollover badge only for rollover envelopes', async () => {
    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()
    const rolloverBadges = wrapper.findAll('.badge-info')
    // Transport has rollover=true, Food does not
    expect(rolloverBadges.length).toBe(1)
  })

  it('shows empty state when no envelopes', async () => {
    const { listEnvelopes } = await import('@/api/envelopes')
    vi.mocked(listEnvelopes).mockResolvedValueOnce([])
    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()
    expect(wrapper.text()).toContain('No envelopes yet')
  })

  it('opens add form on "+ Add envelope" click', async () => {
    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('Add envelope'))
    await addBtn!.trigger('click')
    expect(wrapper.find('input[placeholder="Envelope name"]').exists()).toBe(true)
  })

  it('creates envelope and reloads list', async () => {
    const { createEnvelope, listEnvelopes } = await import('@/api/envelopes')
    const newEnv: Envelope = { id: 3, name: 'Leisure', emoji: '🎮', color_index: null, rollover: false, sort_order: 2, envelope_type: 'regular', period: 'monthly', target_amount: null, stop_on_target: false, categories: [] }

    // Mount with default list first
    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()

    // Mock create and the subsequent reload
    vi.mocked(createEnvelope).mockResolvedValueOnce(newEnv)
    vi.mocked(listEnvelopes).mockResolvedValueOnce([...sampleEnvelopes, newEnv])

    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('Add envelope'))
    await addBtn!.trigger('click')
    const input = wrapper.find('input[placeholder="Envelope name"]')
    await input.setValue('Leisure')
    const createBtn = wrapper.findAll('button').find((b) => b.text().trim() === 'Create')
    await createBtn!.trigger('click')
    await flushPromises()

    expect(createEnvelope).toHaveBeenCalledWith(expect.objectContaining({ name: 'Leisure' }))
    expect(wrapper.text()).toContain('Leisure')
  })

  it('opens edit form on Edit click', async () => {
    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text() === 'Edit')
    await editBtn!.trigger('click')
    // Input should be visible with current name
    const input = wrapper.find('input[placeholder="Envelope name"]')
    expect(input.exists()).toBe(true)
    expect((input.element as HTMLInputElement).value).toBe('Food')
  })

  it('saves edited envelope and reloads', async () => {
    const { updateEnvelope, listEnvelopes } = await import('@/api/envelopes')
    const updated: Envelope = { ...sampleEnvelopes[0]!, name: 'Food & Drink' }

    // Mount with default listEnvelopes (set in beforeEach)
    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()

    // Mock save call and subsequent reload
    vi.mocked(updateEnvelope).mockResolvedValueOnce(updated)
    vi.mocked(listEnvelopes).mockResolvedValueOnce([updated, sampleEnvelopes[1]!])

    const editBtn = wrapper.findAll('button').find((b) => b.text() === 'Edit')
    await editBtn!.trigger('click')
    const input = wrapper.find('input[placeholder="Envelope name"]')
    await input.setValue('Food & Drink')
    const saveBtn = wrapper.findAll('button').find((b) => b.text().trim() === 'Save')
    await saveBtn!.trigger('click')
    await flushPromises()

    expect(updateEnvelope).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ name: 'Food & Drink' }),
    )
  })

  it('cancels edit without saving', async () => {
    const { updateEnvelope } = await import('@/api/envelopes')
    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text() === 'Edit')
    await editBtn!.trigger('click')
    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === 'Cancel')
    await cancelBtn!.trigger('click')
    expect(updateEnvelope).not.toHaveBeenCalled()
    // Edit form should be gone
    expect(wrapper.find('input[placeholder="Envelope name"]').exists()).toBe(false)
  })

  it('deletes envelope after confirm', async () => {
    vi.stubGlobal('confirm', vi.fn().mockReturnValue(true))
    const { deleteEnvelope, listEnvelopes } = await import('@/api/envelopes')

    // Mount first (beforeEach already sets listEnvelopes → sampleEnvelopes)
    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()

    // Now override the reload result and mock the delete
    vi.mocked(deleteEnvelope).mockResolvedValueOnce(undefined)
    vi.mocked(listEnvelopes).mockResolvedValueOnce(sampleEnvelopes.slice(1))

    const deleteBtn = wrapper.findAll('button').find((b) => b.text() === 'Delete')
    await deleteBtn!.trigger('click')
    await flushPromises()

    expect(deleteEnvelope).toHaveBeenCalledWith(1)
  })

  it('does not delete when user cancels confirm', async () => {
    vi.stubGlobal('confirm', vi.fn().mockReturnValue(false))
    const { deleteEnvelope } = await import('@/api/envelopes')

    const wrapper = mount(EnvelopeManager, { props: { groups: [] } })
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find((b) => b.text() === 'Delete')
    await deleteBtn!.trigger('click')
    await flushPromises()

    expect(deleteEnvelope).not.toHaveBeenCalled()
  })
})
