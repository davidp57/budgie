import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RecurringLineMenu from '../RecurringLineMenu.vue'
import type { RecurringLine, RecurringPayment } from '@/api/types'

function payment(overrides: Partial<RecurringPayment> = {}): RecurringPayment {
  return {
    id: 7,
    key: 'STREAMFLIX',
    name: 'Streamflix',
    kind: 'subscription',
    period: 'monthly',
    amount: 1399,
    current_amount: 1399,
    monthly_cost: 1399,
    category_id: null,
    cancelled_at: null,
    last_date: '2026-11-01',
    occurrences: 6,
    status: 'active',
    price_changed: false,
    debits_after_cancellation: [],
    aliases: [],
    ...overrides,
  }
}

function line(overrides: Partial<RecurringLine> = {}): RecurringLine {
  return {
    id: 'sSTREAMFLIX|1399|2026-01-01',
    ref: { payment_id: null, key: 'STREAMFLIX', amount: 1399, period: 'monthly' },
    payment: null,
    name: 'Streamflix',
    key: 'STREAMFLIX',
    label: 'CARTE STREAMFLIX',
    period: 'monthly',
    amount: 1399,
    monthly_cost: 1399,
    first_date: '2026-01-01',
    last_date: '2026-11-01',
    running: true,
    likely_other: false,
    segments: [],
    ...overrides,
  }
}

function mountMenu(l: RecurringLine) {
  return mount(RecurringLineMenu, {
    props: { line: l, groups: [], today: '2026-11-08', busy: false },
  })
}

function items(wrapper: ReturnType<typeof mountMenu>): string[] {
  return wrapper.findAll('[data-test=menu-item]').map((b) => b.text())
}

async function click(wrapper: ReturnType<typeof mountMenu>, label: string): Promise<void> {
  await wrapper.findAll('[data-test=menu-item]').find((b) => b.text() === label)!.trigger('click')
}

describe('RecurringLineMenu', () => {
  it('shows the status of a line', () => {
    expect(mountMenu(line()).find('[data-test=line-status]').text()).toBe('à confirmer')
    expect(
      mountMenu(line({ payment: payment() })).find('[data-test=line-status]').text(),
    ).toBe('abonnement')
    expect(
      mountMenu(line({ payment: payment({ kind: 'other' }) })).find('[data-test=line-status]').text(),
    ).toBe('pas un abonnement')
    expect(
      mountMenu(
        line({ payment: payment({ status: 'cancelled', cancelled_at: '2026-10-01' }) }),
      ).find('[data-test=line-status]').text(),
    ).toBe('résilié le 01/10/2026')
    expect(
      mountMenu(line({ payment: payment({ kind: 'dismissed' }) })).find('[data-test=line-status]').text(),
    ).toBe('ignoré')
  })

  it('offers every correction on a detected line', async () => {
    const wrapper = mountMenu(line())
    expect(items(wrapper)).toEqual([
      '✓ Abonnement',
      'Pas un abonnement',
      'Résilié…',
      'Renommer…',
      'Ignorer',
    ])
    await click(wrapper, '✓ Abonnement')
    expect(wrapper.emitted('action')![0]).toEqual([{ type: 'kind', kind: 'subscription' }])
  })

  it('offers cancelling and undoing it on a subscription', async () => {
    const active = mountMenu(line({ payment: payment() }))
    expect(items(active)).toContain('Résilié…')
    expect(items(active)).toContain('Retirer le classement')
    const cancelled = mountMenu(
      line({ payment: payment({ status: 'cancelled', cancelled_at: '2026-10-01' }) }),
    )
    expect(items(cancelled)).not.toContain('Résilié…')
    await click(cancelled, 'Annuler la résiliation')
    expect(cancelled.emitted('action')![0]).toEqual([{ type: 'cancel', date: null }])
  })

  it('proposes the date of the last debit, in French', async () => {
    const wrapper = mountMenu(line({ payment: payment(), last_date: '2026-10-03' }))
    await click(wrapper, 'Résilié…')
    const input = wrapper.find('[data-test=cancel-date]')
    expect((input.element as HTMLInputElement).value).toBe('03/10/2026')
    await wrapper.find('[data-test=cancel-confirm]').trigger('click')
    expect(wrapper.emitted('action')![0]).toEqual([{ type: 'cancel', date: '2026-10-03' }])
  })

  it('declares a cancellation with a French date', async () => {
    const wrapper = mountMenu(line({ payment: payment() }))
    await click(wrapper, 'Résilié…')
    await wrapper.find('[data-test=cancel-date]').setValue('15/10/2026')
    await wrapper.find('[data-test=cancel-confirm]').trigger('click')
    expect(wrapper.emitted('action')![0]).toEqual([{ type: 'cancel', date: '2026-10-15' }])
  })

  it('refuses a date that does not exist, and says so', async () => {
    const wrapper = mountMenu(line({ payment: payment() }))
    await click(wrapper, 'Résilié…')
    await wrapper.find('[data-test=cancel-date]').setValue('31/02/2026')
    await wrapper.find('[data-test=cancel-confirm]').trigger('click')
    expect(wrapper.emitted('action')).toBeUndefined()
    expect(wrapper.find('[data-test=cancel-error]').text()).toContain('jj/mm/aaaa')
    expect(wrapper.find('[data-test=cancel-date]').exists()).toBe(true)
  })

  it('renames, once even if Enter and blur both fire', async () => {
    const wrapper = mountMenu(line())
    await click(wrapper, 'Renommer…')
    const input = wrapper.find('[data-test=rename-input]')
    await input.setValue('Mon streaming')
    await input.trigger('keydown.enter')
    await input.trigger('blur')
    expect(wrapper.emitted('action')).toEqual([[{ type: 'rename', name: 'Mon streaming' }]])
  })

  it('accepts a new price only when there is one', async () => {
    expect(items(mountMenu(line({ payment: payment() })))).not.toContain('Accepter le nouveau prix')
    const wrapper = mountMenu(line({ payment: payment({ price_changed: true, current_amount: 1599 }) }))
    await click(wrapper, 'Accepter le nouveau prix')
    expect(wrapper.emitted('action')![0]).toEqual([{ type: 'acceptPrice' }])
  })

  it('brings an ignored line back', async () => {
    const wrapper = mountMenu(line({ payment: payment({ kind: 'dismissed' }) }))
    expect(items(wrapper)).toEqual(['Reproposer'])
    await click(wrapper, 'Reproposer')
    expect(wrapper.emitted('action')![0]).toEqual([{ type: 'forget' }])
  })

  it('reclassifies "not a subscription" as a subscription', async () => {
    const wrapper = mountMenu(line({ payment: payment({ kind: 'other' }) }))
    await click(wrapper, '✓ Abonnement')
    expect(wrapper.emitted('action')![0]).toEqual([{ type: 'kind', kind: 'subscription' }])
  })

  it('lists the alerts of a subscription', () => {
    const wrapper = mountMenu(
      line({
        payment: payment({
          status: 'cancelled',
          cancelled_at: '2026-09-01',
          debits_after_cancellation: ['2026-10-05'],
        }),
      }),
    )
    expect(wrapper.text()).toContain('Encore prélevé après la résiliation : 05/10/2026')
  })

  it('offers renaming on every line, stopped ones included', () => {
    expect(items(mountMenu(line({ running: false })))).toContain('Renommer…')
    expect(items(mountMenu(line({ running: false, payment: payment() })))).toContain('Renommer…')
  })

  it('shows the usual corrections as buttons and keeps the rest in the menu', () => {
    const wrapper = mountMenu(line({ payment: payment() }))
    const visible = wrapper
      .findAll('[data-test=menu-item]')
      .filter((b) => !b.element.closest('details'))
      .map((b) => b.text())
    expect(visible).toEqual(['Pas un abonnement', 'Résilié…', 'Renommer…'])
    const inMenu = wrapper.findAll('details [data-test=menu-item]').map((b) => b.text())
    expect(inMenu).toEqual(['Catégorie…', 'Retirer le classement'])
  })

  it('closes the menu on a click elsewhere and on Escape', async () => {
    const wrapper = mount(RecurringLineMenu, {
      props: { line: line(), groups: [], today: '2026-11-08', busy: false },
      attachTo: document.body,
    })
    const details = wrapper.find('details').element as HTMLDetailsElement
    details.open = true
    document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    expect(details.open).toBe(false)
    details.open = true
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(details.open).toBe(false)
    wrapper.unmount()
  })

  it('focuses the name field, and Escape leaves it without renaming', async () => {
    const wrapper = mount(RecurringLineMenu, {
      props: { line: line(), groups: [], today: '2026-11-08', busy: false },
      attachTo: document.body,
    })
    await wrapper
      .findAll('[data-test=menu-item]')
      .find((b) => b.text() === 'Renommer…')!
      .trigger('click')
    await new Promise((r) => setTimeout(r, 0))
    const input = wrapper.find('[data-test=rename-input]')
    expect(document.activeElement).toBe(input.element)
    await input.setValue('Autre nom')
    await input.trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('[data-test=rename-input]').exists()).toBe(false)
    expect(wrapper.emitted('action')).toBeUndefined()
    wrapper.unmount()
  })
})
