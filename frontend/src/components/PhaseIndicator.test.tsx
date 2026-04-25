import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PhaseIndicator } from './PhaseIndicator'

describe('PhaseIndicator', () => {
  it('highlights the active phase', () => {
    render(<PhaseIndicator phase="design" isDesigning={false} />)
    const designStep = screen.getByText('Designing')
    expect(designStep).toHaveClass('active')
  })

  it('shows designing spinner when isDesigning is true', () => {
    render(<PhaseIndicator phase="design" isDesigning={true} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
