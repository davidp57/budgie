import client from './client'
import type { LoginResponse } from './types'

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/api/auth/login', { username, password })
  return data
}

export async function register(username: string, password: string): Promise<void> {
  await client.post('/api/auth/register', { username, password })
}
