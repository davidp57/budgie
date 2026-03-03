import client from './client'
import type { UserPreferences } from './types'

export async function getPreferences(): Promise<UserPreferences> {
  const { data } = await client.get<UserPreferences>('/api/users/me/preferences')
  return data
}

export async function updatePreferences(prefs: Partial<UserPreferences>): Promise<UserPreferences> {
  const { data } = await client.put<UserPreferences>('/api/users/me/preferences', prefs)
  return data
}
