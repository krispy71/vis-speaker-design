// frontend/src/components/DriverCard.tsx
import type { DriverSelection } from '../types'

export function DriverCard({ driver }: { driver: DriverSelection }) {
  return (
    <div style={{
      border: '1px solid #e0e0e0', borderRadius: 8, padding: 14,
      background: 'white', marginBottom: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <strong style={{ textTransform: 'capitalize' }}>{driver.role}</strong>
        <span style={{ fontSize: 12, color: '#888' }}>{driver.manufacturer}</span>
      </div>
      <div style={{ fontSize: 15, fontWeight: 600, margin: '4px 0' }}>{driver.model}</div>
      <div style={{ fontSize: 13, color: '#555', lineHeight: 1.4 }}>{driver.justification}</div>
    </div>
  )
}
