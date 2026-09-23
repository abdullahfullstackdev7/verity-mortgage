import { useState } from 'react'
import { CheckCircle2, HelpCircle, XCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import type { CaseSummary } from '@/lib/types'

type Decision = 'approved' | 'referred' | 'denied'

const RECOMMENDATION_TO_DECISION: Record<string, Decision> = {
  approve: 'approved',
  refer: 'referred',
  deny: 'denied',
}

const DECISION_META: Record<Decision, { label: string; icon: typeof CheckCircle2; className: string }> = {
  approved: { label: 'Approve', icon: CheckCircle2, className: 'border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:text-emerald-400' },
  referred: { label: 'Refer', icon: HelpCircle, className: 'border-amber-600 text-amber-700 hover:bg-amber-50 dark:text-amber-400' },
  denied: { label: 'Deny', icon: XCircle, className: 'border-red-600 text-red-700 hover:bg-red-50 dark:text-red-400' },
}

export function DecisionPanel({
  summary,
  onDecide,
  submitting,
  error,
}: {
  summary: CaseSummary | null
  onDecide: (decision: Decision, overrideReason: string | null) => void
  submitting: boolean
  error: string | null
}) {
  const [selected, setSelected] = useState<Decision | null>(null)
  const [reason, setReason] = useState('')

  const recommendedDecision = summary ? RECOMMENDATION_TO_DECISION[summary.recommendation] : null
  const isOverride = selected !== null && selected !== recommendedDecision

  function handleConfirm() {
    if (!selected) return
    onDecide(selected, reason.trim() ? reason.trim() : null)
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h2 className="text-lg font-semibold text-foreground">Underwriter Decision</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        {recommendedDecision
          ? 'Accept the system recommendation, or override it with a reason.'
          : 'No system recommendation exists yet, so any decision here requires a reason.'}
      </p>

      <div className="mt-4 flex flex-wrap gap-3">
        {(Object.keys(DECISION_META) as Decision[]).map((decision) => {
          const meta = DECISION_META[decision]
          const Icon = meta.icon
          const isRecommended = decision === recommendedDecision
          return (
            <Button
              key={decision}
              variant="outline"
              className={cn(meta.className, selected === decision && 'ring-2 ring-ring')}
              onClick={() => setSelected(decision)}
            >
              <Icon className="size-4" />
              {meta.label}
              {isRecommended ? ' (recommended)' : ''}
            </Button>
          )
        })}
      </div>

      {selected ? (
        <div className="mt-4 space-y-2">
          <Textarea
            placeholder={
              isOverride || !recommendedDecision
                ? 'Required: explain why you are overriding the system recommendation.'
                : 'Optional note.'
            }
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
          />
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <div className="flex gap-2">
            <Button onClick={handleConfirm} disabled={submitting}>
              {submitting ? 'Submitting…' : `Confirm ${DECISION_META[selected].label}`}
            </Button>
            <Button variant="ghost" onClick={() => setSelected(null)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
