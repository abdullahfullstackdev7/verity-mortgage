import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { DiscrepanciesPanel } from './DiscrepanciesPanel'
import type { Discrepancy, DocumentRecord } from '@/lib/types'

const DOCUMENT: DocumentRecord = {
  id: 'doc-1',
  case_id: 'case-1',
  doc_type: 'paystub',
  file_path: '/fake/paystub.pdf',
  uploaded_at: new Date().toISOString(),
  ocr_status: 'completed',
}

function makeDiscrepancy(overrides: Partial<Discrepancy> = {}): Discrepancy {
  return {
    id: 'disc-1',
    case_id: 'case-1',
    field_name: 'income_paystub',
    stated_value: '92000',
    document_value: '70000',
    variance_pct: 23.9,
    severity: 'major',
    source_document_id: 'doc-1',
    ...overrides,
  }
}

describe('DiscrepanciesPanel', () => {
  it('shows an empty state when there are no discrepancies', () => {
    render(
      <DiscrepanciesPanel discrepancies={[]} documents={[]} canVerify={false} onVerify={vi.fn()} verifying={false} />,
    )
    expect(screen.getByText(/no discrepancies found/i)).toBeInTheDocument()
  })

  it('renders each discrepancy with its human-readable field label and source document', () => {
    render(
      <DiscrepanciesPanel
        discrepancies={[makeDiscrepancy()]}
        documents={[DOCUMENT]}
        canVerify={false}
        onVerify={vi.fn()}
        verifying={false}
      />,
    )
    expect(screen.getByText('Income (Pay Stub)')).toBeInTheDocument()
    expect(screen.getByText('92000')).toBeInTheDocument()
    expect(screen.getByText('70000')).toBeInTheDocument()
    expect(screen.getByText('23.9%')).toBeInTheDocument()
    expect(screen.getByText(/source: paystub/i)).toBeInTheDocument()
  })

  it('falls back to the raw field name when no label is known', () => {
    render(
      <DiscrepanciesPanel
        discrepancies={[makeDiscrepancy({ field_name: 'some_new_field' })]}
        documents={[]}
        canVerify={false}
        onVerify={vi.fn()}
        verifying={false}
      />,
    )
    expect(screen.getByText('some_new_field')).toBeInTheDocument()
  })

  it('only shows the verify button when canVerify is true, and calls onVerify when clicked', async () => {
    const user = userEvent.setup()
    const onVerify = vi.fn()
    render(
      <DiscrepanciesPanel discrepancies={[]} documents={[]} canVerify={true} onVerify={onVerify} verifying={false} />,
    )
    const button = screen.getByRole('button', { name: /run verification/i })
    await user.click(button)
    expect(onVerify).toHaveBeenCalledOnce()
  })

  it('disables the verify button and shows a verifying label while verifying', () => {
    render(
      <DiscrepanciesPanel discrepancies={[]} documents={[]} canVerify={true} onVerify={vi.fn()} verifying={true} />,
    )
    expect(screen.getByRole('button', { name: /verifying/i })).toBeDisabled()
  })
})
