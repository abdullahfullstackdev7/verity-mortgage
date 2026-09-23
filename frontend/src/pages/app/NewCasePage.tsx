import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { createCase, listApplicants } from '@/lib/api'
import type { Applicant } from '@/lib/types'

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

export function NewCasePage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [applicants, setApplicants] = useState<Applicant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creatingId, setCreatingId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    const handle = setTimeout(() => {
      listApplicants(search || undefined, 1, 25)
        .then((page) => {
          if (!cancelled) setApplicants(page.items)
        })
        .catch(() => {
          if (!cancelled) setError('Could not load applicants.')
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, 250)
    return () => {
      cancelled = true
      clearTimeout(handle)
    }
  }, [search])

  async function handleCreate(applicantId: string) {
    setCreatingId(applicantId)
    setError(null)
    try {
      const created = await createCase(applicantId)
      navigate(`/app/cases/${created.id}`)
    } catch {
      setError('Could not create a case for this applicant.')
      setCreatingId(null)
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl font-semibold text-foreground">New Case</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Pick an applicant from the seeded HMDA-derived pool to open a new underwriting case.
      </p>

      <Input
        className="mt-6"
        placeholder="Search by applicant or employer name…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {error ? <p className="mt-4 text-sm text-destructive">{error}</p> : null}

      <div className="mt-6 divide-y divide-border rounded-xl border border-border bg-card">
        {loading ? (
          <p className="p-8 text-center text-sm text-muted-foreground">Loading applicants…</p>
        ) : applicants.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">No applicants found.</p>
        ) : (
          applicants.map((applicant) => (
            <div
              key={applicant.id}
              className="flex flex-wrap items-center justify-between gap-4 p-5"
            >
              <div>
                <p className="font-medium text-foreground">{applicant.name}</p>
                <p className="text-sm text-muted-foreground">{applicant.employer_name}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Stated income {currencyFormatter.format(applicant.stated_income)} &middot; Loan
                  amount {currencyFormatter.format(applicant.stated_loan_amount)}
                </p>
              </div>
              <Button
                onClick={() => handleCreate(applicant.id)}
                disabled={creatingId === applicant.id}
              >
                {creatingId === applicant.id ? 'Creating…' : 'Create Case'}
              </Button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
