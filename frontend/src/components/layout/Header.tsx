import { Menu } from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { cn } from '@/lib/utils'

const NAV_LINKS = [
  { label: 'Solutions', to: '/solutions' },
  { label: 'How It Works', to: '/how-it-works' },
  { label: 'Security', to: '/security' },
  { label: 'About', to: '/about' },
  { label: 'Contact', to: '/contact' },
]

function Logo() {
  return (
    <NavLink to="/" className="flex items-center gap-2">
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
      <span className="font-heading text-xl font-semibold tracking-tight text-foreground">
        Verity
      </span>
    </NavLink>
  )
}

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'text-sm font-medium text-muted-foreground transition-colors hover:text-foreground',
          isActive && 'text-foreground',
        )
      }
    >
      {label}
    </NavLink>
  )
}

export function Header() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/70 bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/75">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Logo />

        <nav className="hidden items-center gap-8 lg:flex">
          {NAV_LINKS.map((link) => (
            <NavItem key={link.to} {...link} />
          ))}
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <Button variant="ghost" nativeButton={false} render={<NavLink to="/login" />}>
            Login
          </Button>
          <Button nativeButton={false} render={<NavLink to="/contact" />}>
            Request a Demo
          </Button>
        </div>

        <Sheet>
          <SheetTrigger
            render={
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open menu">
                <Menu className="size-5" />
              </Button>
            }
          />
          <SheetContent side="right" className="w-72">
            <SheetHeader>
              <SheetTitle>
                <Logo />
              </SheetTitle>
            </SheetHeader>
            <nav className="flex flex-col gap-6 px-6 pt-4">
              {NAV_LINKS.map((link) => (
                <NavItem key={link.to} {...link} />
              ))}
              <Separator />
              <NavLink to="/login" className="text-sm font-medium text-muted-foreground">
                Login
              </NavLink>
              <Button nativeButton={false} render={<NavLink to="/contact" />}>
                Request a Demo
              </Button>
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  )
}

function Separator() {
  return <div className="h-px w-full bg-border" />
}
