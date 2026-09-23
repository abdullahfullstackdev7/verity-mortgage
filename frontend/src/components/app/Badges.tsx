import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { CaseStatus, DiscrepancySeverity, OcrStatus, Recommendation } from '@/lib/types'

const STATUS_STYLES: Record<CaseStatus, string> = {
  submitted: 'bg-secondary text-secondary-foreground border-transparent',
  documents_pending: 'bg-amber-100 text-amber-900 border-transparent dark:bg-amber-500/15 dark:text-amber-300',
  under_review: 'bg-blue-100 text-blue-900 border-transparent dark:bg-blue-500/15 dark:text-blue-300',
  approved: 'bg-emerald-100 text-emerald-900 border-transparent dark:bg-emerald-500/15 dark:text-emerald-300',
  referred: 'bg-amber-100 text-amber-900 border-transparent dark:bg-amber-500/15 dark:text-amber-300',
  denied: 'bg-red-100 text-red-900 border-transparent dark:bg-red-500/15 dark:text-red-300',
}

const STATUS_LABELS: Record<CaseStatus, string> = {
  submitted: 'Submitted',
  documents_pending: 'Documents Pending',
  under_review: 'Under Review',
  approved: 'Approved',
  referred: 'Referred',
  denied: 'Denied',
}

export function CaseStatusBadge({ status }: { status: CaseStatus }) {
  return (
    <Badge className={cn('font-medium', STATUS_STYLES[status])}>{STATUS_LABELS[status]}</Badge>
  )
}

const SEVERITY_STYLES: Record<DiscrepancySeverity, string> = {
  minor: 'bg-amber-100 text-amber-900 border-transparent dark:bg-amber-500/15 dark:text-amber-300',
  major: 'bg-red-100 text-red-900 border-transparent dark:bg-red-500/15 dark:text-red-300',
}

export function SeverityBadge({ severity }: { severity: DiscrepancySeverity }) {
  return (
    <Badge className={cn('font-medium capitalize', SEVERITY_STYLES[severity])}>{severity}</Badge>
  )
}

const OCR_STYLES: Record<OcrStatus, string> = {
  pending_ocr: 'bg-secondary text-secondary-foreground border-transparent',
  processing: 'bg-blue-100 text-blue-900 border-transparent dark:bg-blue-500/15 dark:text-blue-300',
  completed: 'bg-emerald-100 text-emerald-900 border-transparent dark:bg-emerald-500/15 dark:text-emerald-300',
  failed: 'bg-red-100 text-red-900 border-transparent dark:bg-red-500/15 dark:text-red-300',
}

const OCR_LABELS: Record<OcrStatus, string> = {
  pending_ocr: 'Pending OCR',
  processing: 'Processing',
  completed: 'Extracted',
  failed: 'Failed',
}

export function OcrStatusBadge({ status }: { status: OcrStatus }) {
  return <Badge className={cn('font-medium', OCR_STYLES[status])}>{OCR_LABELS[status]}</Badge>
}

const RECOMMENDATION_STYLES: Record<Recommendation, string> = {
  approve: 'bg-emerald-100 text-emerald-900 border-transparent dark:bg-emerald-500/15 dark:text-emerald-300',
  refer: 'bg-amber-100 text-amber-900 border-transparent dark:bg-amber-500/15 dark:text-amber-300',
  deny: 'bg-red-100 text-red-900 border-transparent dark:bg-red-500/15 dark:text-red-300',
}

export function RecommendationBadge({ recommendation }: { recommendation: Recommendation }) {
  return (
    <Badge className={cn('font-medium uppercase', RECOMMENDATION_STYLES[recommendation])}>
      {recommendation}
    </Badge>
  )
}
