// frontend/src/App.tsx
import { SessionProvider, useSession } from './context/SessionContext'
import { PhaseIndicator } from './components/PhaseIndicator'
import { ChatPanel } from './components/ChatPanel'
import { ResultsPanel } from './components/ResultsPanel'

function Layout() {
  const { phase, designOutput, bom, sessionId, isDesigning } = useSession()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <PhaseIndicator phase={phase} isDesigning={isDesigning} />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ width: '40%', borderRight: '1px solid #e0e0e0', display: 'flex', flexDirection: 'column' }}>
          <ChatPanel />
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <ResultsPanel
            design={designOutput}
            bom={bom}
            sessionId={sessionId ?? ''}
            phase={phase}
          />
        </div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <SessionProvider>
      <Layout />
    </SessionProvider>
  )
}
