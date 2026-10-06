import { describe, expect, it } from 'vitest'
import { shouldOfferPrfSetup } from '../usePrfStorage'

const base = { supported: true, hasPrfStored: false, passkeyCount: 1, dismissed: false }

describe('shouldOfferPrfSetup', () => {
  it('offers passkey unlock when the account has a passkey and nothing is stored', () => {
    expect(shouldOfferPrfSetup(base)).toBe(true)
  })

  it.each([
    ['the browser lacks WebAuthn or Web Crypto', { supported: false }],
    ['passkey unlock is already set up', { hasPrfStored: true }],
    ['the account has no passkey', { passkeyCount: 0 }],
    ['the user declined on this device', { dismissed: true }],
  ])('does not offer when %s', (_label, override) => {
    expect(shouldOfferPrfSetup({ ...base, ...override })).toBe(false)
  })
})
