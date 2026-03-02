import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EnvelopeCard from '../EnvelopeCard.vue'
import type { EnvelopeLine } from '@/api/types'

const baseEnvelope: EnvelopeLine = {
  category_id: 1,
  category_name: 'Groceries',
  group_id: 10,
  group_name: 'Food',
  budgeted: 20000, // 200.00 €
  activity: -5000, // -50.00 €
  available: 15000, // 150.00 €
}

describe('EnvelopeCard', () => {
  it('renders category name', () => {
    const wrapper = mount(EnvelopeCard, { props: { envelope: baseEnvelope } })
    expect(wrapper.text()).toContain('Groceries')
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
    await wrapper.find('button.btn-ghost').trigger('click') // open edit
    const input = wrapper.find('input')
    await input.setValue('100.50')
    await input.trigger('blur')
    expect(wrapper.emitted('edit')?.[0]).toEqual([10050])
  })
})
