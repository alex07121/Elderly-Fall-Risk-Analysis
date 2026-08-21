import { ofetch } from 'ofetch'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

let _token: string | null = null

async function ensureToken(): Promise<string> {
  if (_token)
    return _token

  const body = new URLSearchParams()
  body.append('username', 'admin_clinician')
  body.append('password', 'password123')

  const res = await ofetch(`${BASE}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })

  _token = res.access_token
  return _token
}

export async function apiGet<T = any>(path: string, query?: Record<string, any>): Promise<T> {
  const token = await ensureToken()
  return ofetch<T>(`${BASE}${path}`, {
    method: 'GET',
    query,
    headers: { Authorization: `Bearer ${token}` },
    timeout: 10000,
  })
}

export async function apiGetById<T = any>(path: string): Promise<T> {
  const token = await ensureToken()
  return ofetch<T>(`${BASE}${path}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
    timeout: 10000,
  })
}

export async function apiDelete<T = any>(path: string): Promise<T> {
  const token = await ensureToken()
  return ofetch<T>(`${BASE}${path}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
    timeout: 10000,
  })
}

export async function apiPost<T = any>(path: string, body?: any): Promise<T> {
  const token = await ensureToken()
  return ofetch<T>(`${BASE}${path}`, {
    method: 'POST',
    body,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    timeout: 10000,
  })
}
