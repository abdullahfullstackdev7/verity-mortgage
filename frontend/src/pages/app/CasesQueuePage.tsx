import { useEffect, useMemo, useState } from 'react'
import { ArrowUpDown, PlusCircle } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

import { CaseStatusBadge } from '@/components/app/Badges'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuth } from '@/lib/auth-context'
import { listCases } from '@/lib/api'
import type { CaseListItem, CaseStatus } from '@/lib/types'

const STATUS_OPTIONS: { value: CaseStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All statuses' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'documents_pending', label: 'Documents Pending' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'approved', label: 'Approved' },
  { value: 'referred', label: 'Referred' },
  { value: 'denied', label: 'Denied' },
]

type SortKey = 'applicant_name' | 'stated_loan_amount' | 'status' | 'discrepancy_count' | 'updated_at'

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

export function CasesQueuePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [cases, setCases] = useState<CaseListItem[]>([])
  const [statusFilter, setStatusFilter] = useState<CaseStatus | 'all'>('all')
  const [sortKey, setSortKey] = useState<SortKey>('updated_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listCases(statusFilter === 'all' ? undefined : statusFilter, 1, 100)
      .then((page) => {
        if (!cancelled) setCases(page.items)
      })
      .catch(() => {
        if (!cancelled) setError('Could not load cases. Is the backend running?')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [statusFilter])

  const sorted = useMemo(() => {
    const items = [...cases]
    items.sort((a, b) => {
      let cmp = 0
      if (sortKey === 'applicant_name') cmp = a.applicant_name.localeCompare(b.applicant_name)
      else if (sortKey === 'stated_loan_amount') cmp = a.stated_loan_amount - b.stated_loan_amount
      else if (sortKey === 'status') cmp = a.status.localeCompare(b.status)
      else if (sortKey === 'discrepancy_count') cmp = a.discrepancy_count - b.discrepancy_count
      else cmp = a.updated_at.localeCompare(b.updated_at)
      return sortDir === 'asc' ? cmp : -cmp
    })
    return items
  }, [cases, sortKey, sortDir])

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const canCreateCase = user?.role === 'loan_officer' || user?.role === 'admin'

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Case Queue</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {loading ? 'Loading cases…' : `${sorted.length} case${sorted.length === 1 ? '' : 's'}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as CaseStatus | 'all')}>
            <SelectTrigger className="w-48">
              <SelectValue>
                {(value: CaseStatus | 'all') =>
                  STATUS_OPTIONS.find((opt) => opt.value === value)?.label ?? value
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {canCreateCase ? (
            <Button render={<Link to="/app/cases/new" />} nativeButton={false}>
              <PlusCircle className="size-4" />
              New Case
            </Button>
          ) : null}
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-xl border border-border bg-card">
        {error ? (
          <p className="p-8 text-center text-sm text-destructive">{error}</p>
        ) : !loading && sorted.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">
            No cases match this filter.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <SortableHead label="Applicant" active={sortKey === 'applicant_name'} onClick={() => toggleSort('applicant_name')} />
                <SortableHead label="Loan Amount" active={sortKey === 'stated_loan_amount'} onClick={() => toggleSort('stated_loan_amount')} />
                <SortableHead label="Status" active={sortKey === 'status'} onClick={() => toggleSort('status')} />
                <SortableHead label="Flags" active={sortKey === 'discrepancy_count'} onClick={() => toggleSort('discrepancy_count')} />
                <TableHead>Assigned Underwriter</TableHead>
                <SortableHead label="Updated" active={sortKey === 'updated_at'} onClick={() => toggleSort('updated_at')} />
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((c) => (
                <TableRow
                  key={c.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/app/cases/${c.id}`)}
                >
                  <TableCell className="font-medium text-foreground">{c.applicant_name}</TableCell>
                  <TableCell>{currencyFormatter.format(c.stated_loan_amount)}</TableCell>
                  <TableCell>
                    <CaseStatusBadge status={c.status} />
                  </TableCell>
                  <TableCell>
                    {c.discrepancy_count === 0 ? (
                      <span className="text-muted-foreground">Clean</span>
                    ) : (
                      <span className={c.major_discrepancy_count > 0 ? 'font-medium text-red-700 dark:text-red-400' : 'text-amber-800 dark:text-amber-400'}>
                        {c.discrepancy_count} flag{c.discrepancy_count === 1 ? '' : 's'}
                        {c.major_discrepancy_count > 0 ? ` (${c.major_discrepancy_count} major)` : ''}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {c.assigned_underwriter_email ?? 'Unassigned'}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(c.updated_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  )
}

function SortableHead({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <TableHead>
      <button
        type="button"
        onClick={onClick}
        className={`flex items-center gap-1 text-xs font-medium uppercase tracking-wide ${active ? 'text-foreground' : 'text-muted-foreground'}`}
      >
        {label}
        <ArrowUpDown className="size-3" />
      </button>
    </TableHead>
  )
}
