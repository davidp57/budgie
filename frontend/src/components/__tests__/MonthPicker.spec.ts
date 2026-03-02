import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MonthPicker from '../MonthPicker.vue'

describe('MonthPicker', () => {
  it('displays a formatted month label', () => {
    const wrapper = mount(MonthPicker, { props: { modelValue: '2024-03' } })
    expect(wrapper.text()).toContain('2024')
  })

  it('emits update:modelValue with previous month on prev click', async () => {
    const wrapper = mount(MonthPicker, { props: { modelValue: '2024-03' } })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['2024-02'])
  })

  it('wraps from January to December of previous year', async () => {
    const wrapper = mount(MonthPicker, { props: { modelValue: '2024-01' } })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['2023-12'])
  })

  it('emits next month on next-arrow click', async () => {
    const wrapper = mount(MonthPicker, { props: { modelValue: '2024-03' } })
    const buttons = wrapper.findAll('button')
    await buttons[2]!.trigger('click') // next button
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['2024-04'])
  })

  it('wraps from December to January of next year', async () => {
    const wrapper = mount(MonthPicker, { props: { modelValue: '2024-12' } })
    const buttons = wrapper.findAll('button')
    await buttons[2]!.trigger('click')
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['2025-01'])
  })
})
