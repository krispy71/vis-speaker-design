import { useEffect, useRef, useState } from 'react'
import { useSession } from '../context/SessionContext'

export function ChatPanel() {
  const { conversation, isLoading, isDesigning, send, start, sessionId } = useSession()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation])

  async function handleSend() {
    const msg = input.trim()
    if (!msg || isLoading) return
    setInput('')
    await send(msg)
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
        {!sessionId && (
          <div style={{ textAlign: 'center', marginTop: 60 }}>
            <h2 style={{ marginBottom: 12 }}>Speaker Designer</h2>
            <p style={{ color: '#666', marginBottom: 20 }}>
              Chat with Marcus, our expert speaker designer, to create your perfect speakers.
            </p>
            <button onClick={start} style={btnStyle}>Start a new design</button>
          </div>
        )}
        {conversation.map((msg, i) => (
          <div
            key={i}
            style={{
              marginBottom: 16,
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div style={{
              maxWidth: '75%',
              padding: '10px 14px',
              borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
              background: msg.role === 'user' ? '#333' : '#fff',
              color: msg.role === 'user' ? 'white' : '#1a1a1a',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              fontSize: 14,
              lineHeight: 1.5,
              whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>
          </div>
        ))}
        {isDesigning && (
          <div style={{ color: '#888', fontSize: 13, textAlign: 'center', marginTop: 8 }}>
            Marcus is designing your speakers… this takes 1-2 minutes.
          </div>
        )}
        {isLoading && !isDesigning && (
          <div style={{ color: '#888', fontSize: 13 }}>Marcus is typing…</div>
        )}
        <div ref={bottomRef} />
      </div>

      {sessionId && !isDesigning && (
        <div style={{ display: 'flex', gap: 8, padding: 16, borderTop: '1px solid #e0e0e0', background: 'white' }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Type your message…"
            rows={2}
            style={{ flex: 1, resize: 'none', padding: '8px 12px', borderRadius: 8, border: '1px solid #ccc', fontSize: 14 }}
          />
          <button onClick={handleSend} disabled={isLoading || !input.trim()} style={btnStyle}>
            Send
          </button>
        </div>
      )}
    </div>
  )
}

const btnStyle: React.CSSProperties = {
  padding: '10px 20px',
  background: '#333',
  color: 'white',
  border: 'none',
  borderRadius: 8,
  cursor: 'pointer',
  fontWeight: 'bold',
  fontSize: 14,
}
