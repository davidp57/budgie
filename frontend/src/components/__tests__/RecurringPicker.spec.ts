import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RecurringPicker from '../RecurringPicker.vue'
import type { RecurringPayment } from '@/api/types'

function payment(id: number, name: string): RecurringPayment {
  return {
    id,
    key: name.toUpperCase(),
    name,
    kind: 'subscription',
    period: 'monthly',
    amount: 999,
    current_amount: 999,
    monthly_cost: 999,
    category_id: null,
    cancelled_at: null,
    last_date: '2026-11-01',
    occurrences: 4,
    status: 'active',
    price_changed: false,
    debits_after_cancellation: [],
    aliases: [],
  }
}

describe('RecurringPicker', () => {
  const props = {
    payments: [payment(1, 'Streaming'), payment(2, 'Musique')],
    prompt: 'Même paiement que :',
    busy: false,
  }

  it('cannot confirm before a payment is chosen', () => {
    const wrapper = mount(RecurringPicker, { props })
    const confirm = wrapper.findAll('button')[0]!
    expect(confirm.attributes('disabled')).toBeDefined()
  })

  it('emits the chosen payment id', async () => {
    const wrapper = mount(RecurringPicker, { props })
    await wrapper.find('select').setValue('2')
    await wrapper.findAll('button')[0]!.trigger('click')
    expect(wrapper.emitted('choose')![0]).toEqual([2])
  })

  it('lists the payments alphabetically', () => {
    const wrapper = mount(RecurringPicker, { props })
    const names = wrapper.findAll('option').slice(1).map((o) => o.text().split(' — ')[0])
    expect(names).toEqual(['Musique', 'Streaming'])
  })

  it('emits cancel', async () => {
    const wrapper = mount(RecurringPicker, { props })
    await wrapper.findAll('button')[1]!.trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })
})
