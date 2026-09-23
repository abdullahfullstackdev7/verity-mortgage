import { FolderKanban, LogOut, PlusCircle, Users } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth-context'
import { cn } from '@/lib/utils'

const NAV_ITEMS: { to: string; label: string; icon: typeof FolderKanban; roles?: string[] }[] = [
  { to: '/app/cases', label: 'Case Queue', icon: FolderKanban },
  { to: '/app/cases/new', label: 'New Case', icon: PlusCircle, roles: ['loan_officer', 'admin'] },
  { to: '/app/users', label: 'Users', icon: Users, roles: ['admin'] },
]

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-svh bg-secondary/30">
      <aside className="hidden w-60 shrink-0 border-r border-border bg-card sm:flex sm:flex-col">
        <div className="flex items-center gap-2 border-b border-border px-6 py-5">
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none" aria-hidden="true">
            <rect width="28" height="28" rx="7" className="fill-primary" />
            <path
              d="M8 13.5L12.2 18L20 9"
              style={{ stroke: 'var(--accent)' }}
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="font-heading text-lg font-semibold tracking-tight">Verity</span>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV_ITEMS.filter((item) => !item.roles || (user && item.roles.includes(user.role))).map(
            (item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/app/cases'}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground',
                      isActive && 'bg-secondary text-foreground',
                    )
                  }
                >
                  <Icon className="size-4" strokeWidth={1.75} />
                  {item.label}
                </NavLink>
              )
            },
          )}
        </nav>

        <div className="border-t border-border p-3">
          <div className="rounded-lg px-3 py-2">
            <p className="truncate text-sm font-medium text-foreground">{user?.email}</p>
            <p className="text-xs capitalize text-muted-foreground">
              {user?.role.replace('_', ' ')}
            </p>
          </div>
          <Button
            variant="ghost"
            className="mt-1 w-full justify-start gap-3 text-muted-foreground"
            onClick={handleLogout}
          >
            <LogOut className="size-4" strokeWidth={1.75} />
            Sign out
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border bg-card px-4 py-3 sm:hidden">
          <span className="font-heading text-lg font-semibold">Verity</span>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            Sign out
          </Button>
        </header>
        <main className="flex-1 px-4 py-8 sm:px-8">{children}</main>
      </div>
    </div>
  )
}
