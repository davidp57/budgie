import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/' }),
  useRouter: () => ({ push }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ logout: vi.fn() }),
}))
vi.mock('@/composables/useUnassignedCount', () => ({
  useUnassignedCount: () => ({ count: ref(0), refresh: vi.fn() }),
}))
vi.mock('@/composables/useAppVersion', () => ({
  useAppVersion: () => ref(''),
}))

import AppNav from '../AppNav.vue'

function dockButtons(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('.dock > button')
}

describe('AppNav', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockClear()
  })

  it('shows the subscriptions entry in the mobile dock, labelled "Abos"', async () => {
    const wrapper = mount(AppNav)
    const entry = dockButtons(wrapper).find((b) => b.find('.dock-label').text() === 'Abos')
    expect(entry).toBeDefined()
    await entry!.trigger('click')
    expect(push).toHaveBeenCalledWith('/abonnements')
  })

  it('keeps seven entries in the mobile dock', () => {
    const wrapper = mount(AppNav)
    expect(dockButtons(wrapper)).toHaveLength(7)
  })

  it('keeps the full "Abonnements" label in the desktop menu', () => {
    const wrapper = mount(AppNav)
    const labels = wrapper.findAll('aside nav button').map((b) => b.text())
    expect(labels).toContain('Abonnements')
    expect(labels).not.toContain('Abos')
  })
})
