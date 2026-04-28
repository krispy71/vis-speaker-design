import type { SessionState, Phase } from '../types'

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const hasBody = init?.body !== undefined
  const response = await fetch(path, {
    headers: hasBody ? { 'Content-Type': 'application/json' } : {},
    ...init,
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`API ${response.status}: ${text}`)
  }
  return response.json() as Promise<T>
}

export function createSession(): Promise<{ session_id: string; phase: string }> {
  return apiFetch('/sessions', { method: 'POST' })
}

export function getSession(sessionId: string): Promise<SessionState> {
  return apiFetch(`/sessions/${sessionId}`)
}

export function sendMessage(
  sessionId: string,
  content: string
): Promise<{ reply: string; phase: Phase; transition: string | null }> {
  return apiFetch(`/sessions/${sessionId}/message`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
}

export function exportPdfUrl(sessionId: string): string {
  return `/sessions/${sessionId}/export/pdf`
}

export function exportCsvUrl(sessionId: string): string {
  return `/sessions/${sessionId}/export/csv`
}
