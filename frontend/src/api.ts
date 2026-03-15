import { API_URL } from './config';

/**
 * Fetch API with Accept: application/json and safe JSON parsing.
 * Throws if response is not JSON (e.g. HTML from SPA fallback).
 */
export async function apiRequest<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: { Accept: 'application/json', ...init?.headers } as HeadersInit,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const ct = res.headers.get('Content-Type') ?? '';
  if (!ct.includes('application/json')) {
    throw new Error(`Expected JSON, got ${ct.split(';')[0].trim() || 'unknown'}`);
  }
  return res.json() as Promise<T>;
}
