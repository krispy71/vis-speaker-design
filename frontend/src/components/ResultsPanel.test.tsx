// frontend/src/components/ResultsPanel.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ResultsPanel } from './ResultsPanel'
import type { DesignOutput, BOM } from '../types'

const mockDesign: DesignOutput = {
  speaker_type: '2-way',
  enclosure_type: 'sealed',
  enclosure_dimensions_mm: { h: 380, w: 210, d: 280 },
  internal_volume_liters: 12.5,
  drivers: [{
    role: 'woofer', manufacturer: 'Dayton Audio', model: 'RS180-8',
    justification: 'Great Qts', ts_params: {}
  }],
  crossover: {
    topology: '2nd order Linkwitz-Riley', crossover_freq_hz: 2200,
    components: [{ type: 'inductor', value: '0.56mH', role: 'L1' }]
  },
  dsp_notes: null,
}

const mockBom: BOM = {
  items: [{
    category: 'drivers', part: 'Woofer', manufacturer: 'Dayton Audio',
    model: 'RS180-8', qty: 2, unit_price: 59.98, extended_price: 119.96, source_url: null
  }],
  subtotals: { drivers: 119.96, crossover: 0, hardware: 0 },
  grand_total: 119.96,
  rationale: 'RS180-8 is well-suited for sealed enclosures.',
}

describe('ResultsPanel', () => {
  it('shows empty state when no design', () => {
    render(<ResultsPanel design={null} bom={null} sessionId="abc" phase="intake" />)
    expect(screen.getByText(/complete your conversation/i)).toBeInTheDocument()
  })

  it('shows speaker type when design is available', () => {
    render(<ResultsPanel design={mockDesign} bom={null} sessionId="abc" phase="design" />)
    expect(screen.getByText(/2-way/i)).toBeInTheDocument()
  })

  it('shows grand total when BOM is available', () => {
    render(<ResultsPanel design={mockDesign} bom={mockBom} sessionId="abc" phase="complete" />)
    expect(screen.getByText(/119\.96/)).toBeInTheDocument()
  })
})
