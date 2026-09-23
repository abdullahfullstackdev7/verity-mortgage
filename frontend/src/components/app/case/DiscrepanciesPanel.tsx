import { ShieldCheck } from 'lucide-react'

import { SeverityBadge } from '@/components/app/Badges'
import { Button } from '@/components/ui/button'
import type { Discrepancy, DocumentRecord } from '@/lib/types'

const FIELD_LABELS: Record<string, string> = {
  income_paystub: 'Income (Pay Stub)',
  income_w2: 'Income (W-2)',
  employer_name_paystub: 'Employer Name (Pay Stub)',
  employer_name_w2: 'Employer Name (W-2)',
  bank_deposit_total: 'Bank Deposit Total',
  debt_to_income_ratio: 'Debt-to-Income Ratio',
}

export function DiscrepanciesPanel({
  discrepancies,
  documents,
  canVerify,
  onVerify,
  verifying,
}: {
  discrepancies: Discrepancy[]
  documents: DocumentRecord[]
  canVerify: boolean
  onVerify: () => void
  verifying: boolean
}) {
  const docLookup = new Map(documents.map((d) => [d.id, d]))

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Why This Was Flagged</h2>
        {canVerify ? (
          <Button variant="outline" size="sm" onClick={onVerify} disabled={verifying}>
            <ShieldCheck className="size-4" />
            {verifying ? 'Verifying…' : 'Run Verification'}
          </Button>
        ) : null}
      </div>

      {discrepancies.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          No discrepancies found. Run verification once documents are extracted to check for
          any.
        </p>
      ) : (
        <div className="mt-4 space-y-3">
          {discrepancies.map((d) => {
            const sourceDoc = d.source_document_id ? docLookup.get(d.source_document_id) : undefined
            return (
              <div key={d.id} className="rounded-lg border border-border p-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">
                    {FIELD_LABELS[d.field_name] ?? d.field_name}
                  </p>
                  <SeverityBadge severity={d.severity} />
                </div>
                <dl className="mt-3 grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <dt className="text-xs text-muted-foreground">Stated</dt>
                    <dd className="text-foreground">{d.stated_value}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Document</dt>
                    <dd className="text-foreground">{d.document_value}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Variance</dt>
                    <dd className="text-foreground">{d.variance_pct}%</dd>
                  </div>
                </dl>
                {sourceDoc ? (
                  <p className="mt-2 text-xs text-muted-foreground">
                    Source: {sourceDoc.doc_type.replace('_', ' ')}
                  </p>
                ) : null}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
