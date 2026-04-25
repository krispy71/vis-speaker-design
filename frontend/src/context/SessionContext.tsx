import {
  createContext, useCallback, useContext, useEffect, useRef, useState
} from 'react'
import type { ChatMessage, DesignOutput, BOM, Phase } from '../types'
import { createSession, sendMessage, getSession } from '../api/client'

interface SessionContextValue {
  sessionId: string | null
  phase: Phase
  conversation: ChatMessage[]
  designOutput: DesignOutput | null
  bom: BOM | null
  isLoading: boolean
  isDesigning: boolean
  error: string | null
  start: () => Promise<void>
  send: (message: string) => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>('intake')
  const [conversation, setConversation] = useState<ChatMessage[]>([])
  const [designOutput, setDesignOutput] = useState<DesignOutput | null>(null)
  const [bom, setBom] = useState<BOM | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isDesigning, setIsDesigning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startPolling = useCallback((id: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    let consecutiveErrors = 0
    pollRef.current = setInterval(async () => {
      try {
        const state = await getSession(id)
        consecutiveErrors = 0
        setPhase(state.phase)
        if (state.design_output) setDesignOutput(state.design_output)
        if (state.bom) setBom(state.bom)
        if (state.phase === 'complete' || state.phase === 'intake') {
          setIsDesigning(false)
          if (pollRef.current) clearInterval(pollRef.current)
        }
      } catch {
        consecutiveErrors++
        if (consecutiveErrors >= 5) {
          setIsDesigning(false)
          if (pollRef.current) clearInterval(pollRef.current)
        }
      }
    }, 2000)
  }, [])

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const start = useCallback(async () => {
    setError(null)
    setIsLoading(true)
    try {
      const { session_id } = await createSession()
      setSessionId(session_id)
      setPhase('intake')
      setConversation([])
      setDesignOutput(null)
      setBom(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start session')
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const send = useCallback(async (content: string) => {
    if (!sessionId) return
    setError(null)
    setConversation(prev => [...prev, { role: 'user', content }])
    setIsLoading(true)
    try {
      const result = await sendMessage(sessionId, content)
      setConversation(prev => [...prev, { role: 'assistant', content: result.reply }])
      setPhase(result.phase)
      if (result.transition === 'designing') {
        setIsDesigning(true)
        startPolling(sessionId)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [sessionId, startPolling])

  return (
    <SessionContext.Provider value={{
      sessionId, phase, conversation, designOutput, bom,
      isLoading, isDesigning, error, start, send,
    }}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used inside SessionProvider')
  return ctx
}
