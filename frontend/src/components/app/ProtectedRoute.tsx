import { Link, Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '@/lib/auth-context'
import type { UserRole } from '@/lib/types'

export function ProtectedRoute({
  children,
  roles,
}: {
  children: React.ReactNode
  roles?: UserRole[]
}) {
  const { user, status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <div className="flex min-h-svh items-center justify-center text-sm text-muted-foreground">
        Loading&hellip;
      </div>
    )
  }

  if (status === 'unauthenticated' || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (roles && !roles.includes(user.role)) {
    return (
      <div className="flex min-h-svh flex-col items-center justify-center gap-2 px-6 text-center">
        <h1 className="text-xl font-semibold text-foreground">Not authorized</h1>
        <p className="text-sm text-muted-foreground">
          Your role ({user.role.replace('_', ' ')}) doesn&apos;t have access to this page.
        </p>
        <Link to="/app/cases" className="mt-2 text-sm font-medium text-accent hover:underline">
          &larr; Back to the case queue
        </Link>
      </div>
    )
  }

  return <>{children}</>
}
