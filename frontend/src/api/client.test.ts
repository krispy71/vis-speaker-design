import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createSession, sendMessage, getSession } from './client'

const mockFetch = vi.fn()
global.fetch = mockFetch

beforeEach(() => mockFetch.mockReset())

describe('createSession', () => {
  it('calls POST /sessions and returns session_id and phase', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ session_id: 'abc-123', phase: 'intake' }),
    })
    const result = await createSession()
    expect(result.session_id).toBe('abc-123')
    expect(mockFetch).toHaveBeenCalledWith('/sessions', expect.objectContaining({ method: 'POST' }))
  })
})

describe('sendMessage', () => {
  it('calls POST /sessions/:id/message with content', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ reply: 'Hello', phase: 'intake', transition: null }),
    })
    const result = await sendMessage('abc-123', 'I want speakers')
    expect(result.reply).toBe('Hello')
    expect(mockFetch).toHaveBeenCalledWith(
      '/sessions/abc-123/message',
      expect.objectContaining({ method: 'POST' })
    )
  })
})
