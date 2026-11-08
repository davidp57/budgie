import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RecurringPicker from '../RecurringPicker.vue'

describe('RecurringPicker', () => {
  const props = {
    options: [
      { id: 'p1', label: 'Streaming — 13,99 €' },
      { id: 's2', label: 'Musique — 9,99 €' },
    ],
    prompt: 'Même service que :',
    busy: false,
  }

  it('cannot confirm before an item is chosen', () => {
    const wrapper = mount(RecurringPicker, { props })
    expect(wrapper.findAll('button')[0]!.attributes('disabled')).toBeDefined()
  })

  it('emits the chosen id', async () => {
    const wrapper = mount(RecurringPicker, { props })
    await wrapper.find('select').setValue('s2')
    await wrapper.findAll('button')[0]!.trigger('click')
    expect(wrapper.emitted('choose')![0]).toEqual(['s2'])
  })

  it('lists the items alphabetically', () => {
    const wrapper = mount(RecurringPicker, { props })
    const labels = wrapper.findAll('option').slice(1).map((o) => o.text())
    expect(labels).toEqual(['Musique — 9,99 €', 'Streaming — 13,99 €'])
  })

  it('emits cancel', async () => {
    const wrapper = mount(RecurringPicker, { props })
    await wrapper.findAll('button')[1]!.trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })
})
