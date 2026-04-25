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

  it('start() sets session id from createSession', async () => {
    vi.mocked(client.createSession).mockResolvedValueOnce({ session_id: 'sess-1', phase: 'intake' })

    let capturedStart: (() => Promise<void>) | null = null
    function TestStarter() {
      const { sessionId, start } = useSession()
      capturedStart = start
      return <span data-testid="session-id">{sessionId ?? 'none'}</span>
    }

    render(<SessionProvider><TestStarter /></SessionProvider>)
    expect(screen.getByTestId('session-id').textContent).toBe('none')

    await act(async () => {
      await capturedStart!()
    })

    expect(screen.getByTestId('session-id').textContent).toBe('sess-1')
    expect(vi.mocked(client.createSession)).toHaveBeenCalledOnce()
  })
})
