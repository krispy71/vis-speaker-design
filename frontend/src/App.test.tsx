// frontend/src/App.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'
import * as client from './api/client'

vi.mock('./api/client')

describe('App', () => {
  it('renders Start a new design button on load', () => {
    render(<App />)
    expect(screen.getByText(/start a new design/i)).toBeInTheDocument()
  })

  it('renders two panels', () => {
    render(<App />)
    // Left panel has chat area, right has results placeholder
    expect(screen.getByText(/complete your conversation/i)).toBeInTheDocument()
  })
})
