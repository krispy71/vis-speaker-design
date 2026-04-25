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
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startPolling = useCallback((id: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const state = await getSession(id)
        setPhase(state.phase)
        if (state.design_output) setDesignOutput(state.design_output)
        if (state.bom) setBom(state.bom)
        if (state.phase === 'complete' || state.phase === 'intake') {
          setIsDesigning(false)
          if (pollRef.current) clearInterval(pollRef.current)
        }
      } catch {
        // ignore transient errors during polling
      }
    }, 2000)
  }, [])

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const start = useCallback(async () => {
    setIsLoading(true)
    try {
      const { session_id } = await createSession()
      setSessionId(session_id)
      setPhase('intake')
      setConversation([])
      setDesignOutput(null)
      setBom(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const send = useCallback(async (content: string) => {
    if (!sessionId) return
    setConversation(prev => [...prev, { role: 'user', content }])
    setIsLoading(true)
    try {
      const result = await sendMessage(sessionId, content)
      setConversation(prev => [...prev, { role: 'assistant', content: result.reply }])
      setPhase(result.phase as Phase)
      if (result.transition === 'designing') {
        setIsDesigning(true)
        startPolling(sessionId)
      }
    } finally {
      setIsLoading(false)
    }
  }, [sessionId, startPolling])

  return (
    <SessionContext.Provider value={{
      sessionId, phase, conversation, designOutput, bom,
      isLoading, isDesigning, start, send,
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
