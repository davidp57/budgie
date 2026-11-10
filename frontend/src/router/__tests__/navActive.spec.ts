import { describe, expect, it } from 'vitest'
import { isNavActive } from '../navActive'

describe('isNavActive', () => {
  it('lights an entry on its own page and on the pages under it', () => {
    expect(isNavActive('/abonnements', '/abonnements')).toBe(true)
    expect(isNavActive('/abonnements/gerer', '/abonnements')).toBe(true)
  })

  it('does not light an entry on another page sharing its prefix', () => {
    expect(isNavActive('/abonnementsx', '/abonnements')).toBe(false)
    expect(isNavActive('/budget', '/abonnements')).toBe(false)
  })

  it('lights Home on the home page only', () => {
    expect(isNavActive('/', '/')).toBe(true)
    expect(isNavActive('/budget', '/')).toBe(false)
  })
})
