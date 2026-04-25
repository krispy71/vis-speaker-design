// frontend/src/components/ResultsPanel.tsx
import type { DesignOutput, BOM, Phase } from '../types'
import { DriverCard } from './DriverCard'
import { BomTable } from './BomTable'
import { ExportButtons } from './ExportButtons'

interface Props {
  design: DesignOutput | null
  bom: BOM | null
  sessionId: string
  phase: Phase
}

export function ResultsPanel({ design, bom, sessionId, phase }: Props) {
  if (!design) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#999' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🔊</div>
        <p>Complete your conversation with Marcus to see your speaker design here.</p>
      </div>
    )
  }

  const { h, w, d } = design.enclosure_dimensions_mm

  return (
    <div style={{ padding: 20, overflowY: 'auto', height: '100%' }}>
      <div style={{ background: '#333', color: 'white', borderRadius: 10, padding: 16, marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, marginBottom: 6 }}>
          {design.speaker_type} — {design.enclosure_type}
        </h2>
        <div style={{ fontSize: 13, color: '#ccc' }}>
          {h}mm H × {w}mm W × {d}mm D &nbsp;|&nbsp; {design.internal_volume_liters}L internal &nbsp;|&nbsp; {design.crossover.topology} @ {design.crossover.crossover_freq_hz}Hz
        </div>
        {design.dsp_notes && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#ffd' }}>DSP: {design.dsp_notes}</div>
        )}
      </div>

      <h3 style={{ marginBottom: 10 }}>Drivers</h3>
      {design.drivers.map((d, i) => <DriverCard key={i} driver={d} />)}

      <h3 style={{ margin: '20px 0 10px' }}>Crossover Components</h3>
      <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: '#eee' }}>
            <th style={{ padding: '5px 10px', textAlign: 'left' }}>Type</th>
            <th style={{ padding: '5px 10px', textAlign: 'left' }}>Value</th>
            <th style={{ padding: '5px 10px', textAlign: 'left' }}>Role</th>
          </tr>
        </thead>
        <tbody>
          {design.crossover.components.map((c, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: '4px 10px', textTransform: 'capitalize' }}>{c.type}</td>
              <td style={{ padding: '4px 10px', fontFamily: 'monospace' }}>{c.value}</td>
              <td style={{ padding: '4px 10px', color: '#555' }}>{c.role}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {bom && (
        <>
          <h3 style={{ margin: '20px 0 10px' }}>Bill of Materials</h3>
          {phase === 'complete' && <ExportButtons sessionId={sessionId} />}
          <BomTable bom={bom} />
        </>
      )}

      {phase === 'bom' && (
        <div style={{ color: '#888', fontSize: 13, marginTop: 12 }}>
          Assembling bill of materials…
        </div>
      )}
    </div>
  )
}
