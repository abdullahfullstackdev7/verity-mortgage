import { useCallback, useEffect, useState } from 'react'
import { ArrowRight, Route as RouteIcon } from 'lucide-react'
import { useParams } from 'react-router-dom'

import { CaseStatusBadge } from '@/components/app/Badges'
import { AuditTrailPanel } from '@/components/app/case/AuditTrailPanel'
import { DecisionPanel } from '@/components/app/case/DecisionPanel'
import { DiscrepanciesPanel } from '@/components/app/case/DiscrepanciesPanel'
import { DocumentsPanel } from '@/components/app/case/DocumentsPanel'
import { SummaryPanel } from '@/components/app/case/SummaryPanel'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth-context'
import {
  ApiError,
  decideCase,
  generateSummary,
  getApplicant,
  getCase,
  getSummary,
  listAuditLog,
  listDiscrepancies,
  listDocuments,
  routeCase,
  submitForReview,
  verifyCase,
} from '@/lib/api'
import type {
  Applicant,
  AuditLogEntry,
  Case,
  CaseSummary,
  Discrepancy,
  DocumentRecord,
} from '@/lib/types'

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

export function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const { user } = useAuth()

  const [caseData, setCaseData] = useState<Case | null>(null)
  const [applicant, setApplicant] = useState<Applicant | null>(null)
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [discrepancies, setDiscrepancies] = useState<Discrepancy[]>([])
  const [summary, setSummary] = useState<CaseSummary | null>(null)
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [actionError, setActionError] = useState<string | null>(null)
  const [submittingReview, setSubmittingReview] = useState(false)
  const [routing, setRouting] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [generatingSummary, setGeneratingSummary] = useState(false)
  const [summaryError, setSummaryError] = useState<string | null>(null)
  const [decisionSubmitting, setDecisionSubmitting] = useState(false)
  const [decisionError, setDecisionError] = useState<string | null>(null)

  const loadAll = useCallback(async () => {
    if (!caseId) return
    setError(null)
    try {
      const c = await getCase(caseId)
      setCaseData(c)
      const [applicantData, docs, discs, sum, log] = await Promise.all([
        getApplicant(c.applicant_id),
        listDocuments(caseId),
        listDiscrepancies(caseId),
        getSummary(caseId),
        listAuditLog(caseId),
      ])
      setApplicant(applicantData)
      setDocuments(docs)
      setDiscrepancies(discs)
      setSummary(sum)
      setAuditLog(log)
    } catch {
      setError('Could not load this case.')
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  if (!caseId) return null

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading case…</p>
  }
  if (error || !caseData || !applicant) {
    return <p className="text-sm text-destructive">{error ?? 'Case not found.'}</p>
  }

  const isLoanOfficer = user?.role === 'loan_officer' || user?.role === 'admin'
  const isUnderwriter = user?.role === 'underwriter' || user?.role === 'admin'
  const canActOnCase = isLoanOfficer || isUnderwriter

  const canSubmitForReview =
    isLoanOfficer && (caseData.status === 'submitted' || caseData.status === 'documents_pending')
  const canRoute = canActOnCase && caseData.status === 'under_review'
  const canDecide = isUnderwriter && (caseData.status === 'under_review' || caseData.status === 'referred')

  async function handleSubmitForReview() {
    setSubmittingReview(true)
    setActionError(null)
    try {
      await submitForReview(caseId!)
      await loadAll()
    } catch (err) {
      setActionError(err instanceof ApiError ? String(err.detail) : 'Could not submit for review.')
    } finally {
      setSubmittingReview(false)
    }
  }

  async function handleRoute() {
    setRouting(true)
    setActionError(null)
    try {
      await routeCase(caseId!)
      await loadAll()
    } catch (err) {
      setActionError(err instanceof ApiError ? String(err.detail) : 'Could not route this case.')
    } finally {
      setRouting(false)
    }
  }

  async function handleVerify() {
    setVerifying(true)
    try {
      await verifyCase(caseId!, true)
      await loadAll()
    } finally {
      setVerifying(false)
    }
  }

  async function handleGenerateSummary() {
    setGeneratingSummary(true)
    setSummaryError(null)
    try {
      await generateSummary(caseId!, true)
      await loadAll()
    } catch (err) {
      setSummaryError(
        err instanceof ApiError
          ? String(err.detail)
          : 'Could not generate a summary. Is an LLM provider configured on the backend?',
      )
    } finally {
      setGeneratingSummary(false)
    }
  }

  async function handleDecide(decision: 'approved' | 'referred' | 'denied', overrideReason: string | null) {
    setDecisionSubmitting(true)
    setDecisionError(null)
    try {
      await decideCase(caseId!, decision, overrideReason)
      await loadAll()
    } catch (err) {
      setDecisionError(err instanceof ApiError ? String(err.detail) : 'Could not record decision.')
    } finally {
      setDecisionSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-foreground">{applicant.name}</h1>
            <CaseStatusBadge status={caseData.status} />
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{applicant.employer_name}</p>
        </div>
        <div className="flex items-center gap-2">
          {canSubmitForReview ? (
            <Button onClick={handleSubmitForReview} disabled={submittingReview}>
              <ArrowRight className="size-4" />
              {submittingReview ? 'Submitting…' : 'Submit for Review'}
            </Button>
          ) : null}
          {canRoute ? (
            <Button variant="outline" onClick={handleRoute} disabled={routing}>
              <RouteIcon className="size-4" />
              {routing ? 'Routing…' : 'Auto-Route'}
            </Button>
          ) : null}
        </div>
      </div>
      {actionError ? <p className="mt-2 text-sm text-destructive">{actionError}</p> : null}

      <dl className="mt-6 grid grid-cols-2 gap-4 rounded-xl border border-border bg-card p-6 sm:grid-cols-4">
        <Figure label="Stated Income" value={currencyFormatter.format(applicant.stated_income)} />
        <Figure label="Loan Amount" value={currencyFormatter.format(applicant.stated_loan_amount)} />
        <Figure label="Property Value" value={currencyFormatter.format(applicant.stated_property_value)} />
        <Figure label="Stated DTI" value={`${applicant.stated_dti}%`} />
      </dl>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <DocumentsPanel
            caseId={caseId}
            documents={documents}
            canUpload={isLoanOfficer}
            canExtract={canActOnCase}
            onDocumentsChanged={loadAll}
          />
        </div>
        <div className="space-y-6">
          <DiscrepanciesPanel
            discrepancies={discrepancies}
            documents={documents}
            canVerify={canActOnCase}
            onVerify={handleVerify}
            verifying={verifying}
          />
          <SummaryPanel
            summary={summary}
            canGenerate={canActOnCase}
            onGenerate={handleGenerateSummary}
            generating={generatingSummary}
            generateError={summaryError}
          />
          {canDecide ? (
            <DecisionPanel
              summary={summary}
              onDecide={handleDecide}
              submitting={decisionSubmitting}
              error={decisionError}
            />
          ) : null}
          <AuditTrailPanel entries={auditLog} />
        </div>
      </div>
    </div>
  )
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 text-lg font-semibold text-foreground">{value}</dd>
    </div>
  )
}
