import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { DecisionPanel } from './DecisionPanel'
import type { CaseSummary, Recommendation } from '@/lib/types'

function makeSummary(recommendation: Recommendation): CaseSummary {
  return {
    id: 'summary-1',
    case_id: 'case-1',
    narrative_text: 'Test narrative',
    recommendation,
    generated_by_model: 'test-model',
    token_count: null,
    created_at: new Date().toISOString(),
  }
}

describe('DecisionPanel', () => {
  it('shows no decision buttons selected and hides the reason field initially', () => {
    render(<DecisionPanel summary={null} onDecide={vi.fn()} submitting={false} error={null} />)
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/required|optional note/i)).not.toBeInTheDocument()
  })

  it('marks the recommended decision from the summary', () => {
    render(<DecisionPanel summary={makeSummary('approve')} onDecide={vi.fn()} submitting={false} error={null} />)
    expect(screen.getByRole('button', { name: /approve \(recommended\)/i })).toBeInTheDocument()
  })

  it('submits the selected decision with a trimmed reason', async () => {
    const user = userEvent.setup()
    const onDecide = vi.fn()
    render(<DecisionPanel summary={makeSummary('approve')} onDecide={onDecide} submitting={false} error={null} />)

    await user.click(screen.getByRole('button', { name: /deny/i }))
    const textarea = screen.getByPlaceholderText(/required: explain why/i)
    await user.type(textarea, '  applicant income cannot be verified  ')
    await user.click(screen.getByRole('button', { name: /confirm deny/i }))

    expect(onDecide).toHaveBeenCalledWith('denied', 'applicant income cannot be verified')
  })

  it('submits null for an empty reason on a non-override decision', async () => {
    const user = userEvent.setup()
    const onDecide = vi.fn()
    render(<DecisionPanel summary={makeSummary('approve')} onDecide={onDecide} submitting={false} error={null} />)

    await user.click(screen.getByRole('button', { name: /approve \(recommended\)/i }))
    await user.click(screen.getByRole('button', { name: /confirm approve/i }))

    expect(onDecide).toHaveBeenCalledWith('approved', null)
  })

  it('disables the confirm button and shows a submitting label while submitting', async () => {
    const user = userEvent.setup()
    render(<DecisionPanel summary={makeSummary('approve')} onDecide={vi.fn()} submitting={true} error={null} />)

    await user.click(screen.getByRole('button', { name: /approve \(recommended\)/i }))
    const confirmButton = screen.getByRole('button', { name: /submitting/i })
    expect(confirmButton).toBeDisabled()
  })

  it('renders a server-side error message', async () => {
    const user = userEvent.setup()
    render(
      <DecisionPanel
        summary={makeSummary('approve')}
        onDecide={vi.fn()}
        submitting={false}
        error="Case is not in a decidable state."
      />,
    )
    await user.click(screen.getByRole('button', { name: /approve \(recommended\)/i }))
    expect(screen.getByText('Case is not in a decidable state.')).toBeInTheDocument()
  })
})
