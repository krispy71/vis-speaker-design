import type { Phase } from '../types'

const STEPS: { key: Phase; label: string }[] = [
  { key: 'intake', label: 'Gathering requirements' },
  { key: 'design', label: 'Designing' },
  { key: 'bom', label: 'Generating BOM' },
  { key: 'complete', label: 'Complete' },
]

const ORDER: Record<Phase, number> = { intake: 0, design: 1, bom: 2, complete: 3 }

interface Props {
  phase: Phase
  isDesigning: boolean
}

export function PhaseIndicator({ phase, isDesigning }: Props) {
  return (
    <div style={{ display: 'flex', gap: 8, padding: '10px 16px', background: '#222', color: '#ccc', fontSize: 13 }}>
      {STEPS.map(step => {
        const stepOrder = ORDER[step.key]
        const currentOrder = ORDER[phase]
        const isDone = stepOrder < currentOrder
        const isActive = step.key === phase
        return (
          <span
            key={step.key}
            className={isActive ? 'active' : isDone ? 'done' : 'pending'}
            style={{
              padding: '2px 10px',
              borderRadius: 12,
              background: isActive ? '#e8d5a3' : isDone ? '#4caf50' : 'transparent',
              color: isActive ? '#333' : isDone ? 'white' : '#888',
              fontWeight: isActive ? 'bold' : 'normal',
            }}
          >
            {step.label}
            {isActive && isDesigning && (
              <span role="status" aria-label="designing" style={{ marginLeft: 6 }}>⏳</span>
            )}
          </span>
        )
      })}
    </div>
  )
}
