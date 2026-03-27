import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EnvelopeCard from '../EnvelopeCard.vue'
import type { EnvelopeLine } from '@/api/types'

const baseEnvelope: EnvelopeLine = {
  envelope_id: 1,
  envelope_name: 'Food',
  envelope_type: 'regular',
  emoji: '🍞',
  color_index: null,
  rollover: false,
  target_amount: null,
  categories: [{ id: 1, name: 'Groceries', group_name: 'Food' }],
  budgeted: 20000, // 200.00 €
  activity: -5000, // -50.00 €
  available: 15000, // 150.00 €
}

describe('EnvelopeCard', () => {
  it('renders envelope name', () => {
    const wrapper = mount(EnvelopeCard, { props: { envelope: baseEnvelope } })
    expect(wrapper.text()).toContain('Food')
  })

  it('renders category chips as subtitle', () => {
    const wrapper = mount(EnvelopeCard, { props: { envelope: baseEnvelope } })
    expect(wrapper.text()).toContain('Groceries')
  })

  it('shows rollover badge when rollover is true', () => {
    const withRollover = { ...baseEnvelope, rollover: true }
    const wrapper = mount(EnvelopeCard, { props: { envelope: withRollover } })
    expect(wrapper.text()).toContain('↻')
  })

  it('does not show rollover badge when rollover is false', () => {
    const wrapper = mount(EnvelopeCard, { props: { envelope: baseEnvelope } })
    expect(wrapper.text()).not.toContain('↻')
  })

  it('shows available in green when positive', () => {
    const wrapper = mount(EnvelopeCard, { props: { envelope: baseEnvelope } })
    const available = wrapper.findAll('span').find((s) => s.classes('text-success'))
    expect(available).toBeTruthy()
  })

  it('shows available in red when negative', () => {
    const neg = { ...baseEnvelope, available: -1000 }
    const wrapper = mount(EnvelopeCard, { props: { envelope: neg } })
    const available = wrapper.findAll('span').find((s) => s.classes('text-error'))
    expect(available).toBeTruthy()
  })

  it('emits edit event with centimes after blur', async () => {
    const wrapper = mount(EnvelopeCard, { props: { envelope: baseEnvelope } })
    // The budgeted-amount button has class tabular-nums; the ⋮ menu button does not
    await wrapper.find('button.btn-ghost.tabular-nums').trigger('click') // open edit
    const input = wrapper.find('input[type="number"]')
    await input.setValue('100.50')
    await input.trigger('blur')
    expect(wrapper.emitted('edit')?.[0]).toEqual([10050])
  })
})
