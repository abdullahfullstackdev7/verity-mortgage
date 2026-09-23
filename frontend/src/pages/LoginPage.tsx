import { type FormEvent, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { isApiError, useAuth } from '@/lib/auth-context'

export function LoginPage() {
  const { login, status } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (status === 'authenticated') {
      const from = (location.state as { from?: string } | null)?.from ?? '/app/cases'
      navigate(from, { replace: true })
    }
  }, [status, location.state, navigate])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      const from = (location.state as { from?: string } | null)?.from ?? '/app/cases'
      navigate(from, { replace: true })
    } catch (err) {
      if (isApiError(err) && err.status === 401) {
        setError('Incorrect email or password.')
      } else {
        setError('Something went wrong signing you in. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-secondary/40 px-6 py-16">
      <Link
        to="/"
        className="mb-10 flex items-center gap-2 text-foreground"
        aria-label="Verity home"
      >
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <rect width="28" height="28" rx="7" className="fill-primary" />
          <path
            d="M8 13.5L12.2 18L20 9"
            style={{ stroke: 'var(--accent)' }}
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="font-heading text-xl font-semibold tracking-tight">Verity</span>
      </Link>

      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-foreground">Sign in to Verity</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Access to the underwriting application is by invitation only.
        </p>

        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="email">Work email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              placeholder="you@lender.com"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </div>

      <Link to="/" className="mt-8 text-sm text-muted-foreground hover:text-foreground">
        &larr; Back to the homepage
      </Link>
    </div>
  )
}
