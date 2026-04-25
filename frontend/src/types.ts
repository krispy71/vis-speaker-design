export type Phase = 'intake' | 'design' | 'bom' | 'complete'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface CrossoverComponent {
  type: string
  value: string
  role: string
}

export interface Crossover {
  topology: string
  crossover_freq_hz: number
  components: CrossoverComponent[]
}

export interface DriverSelection {
  role: string
  manufacturer: string
  model: string
  justification: string
  ts_params: Record<string, unknown>
}

export interface DesignOutput {
  speaker_type: string
  enclosure_type: string
  enclosure_dimensions_mm: { h: number; w: number; d: number }
  internal_volume_liters: number
  drivers: DriverSelection[]
  crossover: Crossover
  dsp_notes: string | null
}

export interface BOMItem {
  category: string
  part: string
  manufacturer: string
  model: string
  qty: number
  unit_price: number
  extended_price: number
  source_url: string | null
}

export interface BOM {
  items: BOMItem[]
  subtotals: Record<string, number>
  grand_total: number
  rationale: string
}

export interface SessionState {
  id: string
  phase: Phase
  conversation: ChatMessage[]
  design_brief: Record<string, unknown> | null
  design_output: DesignOutput | null
  bom: BOM | null
}
