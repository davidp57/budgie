/**
 * Removal of the former PIN unlock data.
 *
 * Earlier versions could keep the encryption passphrase in localStorage,
 * wrapped by a key derived from a 4–6 digit PIN.  A PIN that short can be
 * brute-forced offline from a copy of the browser profile, so the feature
 * was removed; this purges what it left behind on each device.
 */

export const LEGACY_PIN_KEYS = ['budgie_pin_wrap', 'budgie_pin_attempts'] as const

/** Delete any PIN-wrapped passphrase left in localStorage by older versions. */
export function purgeLegacyPinStorage(): void {
  try {
    for (const key of LEGACY_PIN_KEYS) localStorage.removeItem(key)
  } catch {
    // localStorage unavailable (private mode, blocked storage): nothing to purge
  }
}
