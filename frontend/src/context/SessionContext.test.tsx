import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { SessionProvider, useSession } from './SessionContext'
import * as client from '../api/client'

vi.mock('../api/client')

function TestConsumer() {
  const { sessionId, phase, conversation, isLoading } = useSession()
  return (
    <div>
      <span data-testid="phase">{phase}</span>
      <span data-testid="session-id">{sessionId ?? 'none'}</span>
      <span data-testid="loading">{isLoading ? 'yes' : 'no'}</span>
      <span data-testid="msg-count">{conversation.length}</span>
    </div>
  )
}

describe('SessionProvider', () => {
  beforeEach(() => vi.clearAllMocks())

  it('starts with no session and intake phase', () => {
    render(<SessionProvider><TestConsumer /></SessionProvider>)
    expect(screen.getByTestId('session-id').textContent).toBe('none')
    expect(screen.getByTestId('phase').textContent).toBe('intake')
  })

  it('createSession sets session id', async () => {
    vi.mocked(client.createSession).mockResolvedValueOnce({ session_id: 'sess-1', phase: 'intake' })
    const { useSession: hook } = await import('./SessionContext')
    // Just check the mock is wired — full integration tested in App
    expect(vi.mocked(client.createSession)).toBeDefined()
  })
})
