import { FileClock, KeyRound, Lock, ShieldCheck } from 'lucide-react'

import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

const POINTS = [
  {
    icon: Lock,
    title: 'Encrypted by default',
    description: 'Data is encrypted in transit and at rest, with secrets never committed to source control.',
  },
  {
    icon: KeyRound,
    title: 'Role-based access',
    description: 'Loan officers, underwriters, and admins each see only the screens and actions their role permits.',
  },
  {
    icon: FileClock,
    title: 'Full audit trail',
    description: 'Every status change is logged with its actor and the specific evidence that triggered it.',
  },
  {
    icon: ShieldCheck,
    title: 'Human final say',
    description: 'The system can recommend, but only a licensed underwriter can approve or deny a case.',
  },
]

export function SecurityCallout() {
  return (
    <div className="rounded-2xl bg-primary px-8 py-14 text-primary-foreground sm:px-14">
      <div className="grid gap-12 lg:grid-cols-[1fr_1.2fr] lg:items-center">
        <div>
          <p className="text-sm font-semibold tracking-wide text-accent uppercase">
            Security &amp; Compliance
          </p>
          <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
            Built for teams that answer to auditors.
          </h2>
          <p className="mt-4 max-w-md text-base leading-relaxed text-primary-foreground/80">
            Every recommendation the system makes is explainable, and every decision a human
            makes is recorded. Nothing moves through the pipeline unaccounted for.
          </p>
          <Button
            variant="secondary"
            className="mt-6"
            nativeButton={false}
            render={<Link to="/security" />}
          >
            Review our security practices
          </Button>
        </div>

        <div className="grid gap-6 sm:grid-cols-2">
          {POINTS.map((point) => {
            const Icon = point.icon
            return (
              <div key={point.title} className="flex gap-4">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary-foreground/10">
                  <Icon className="size-5 text-accent" strokeWidth={1.75} />
                </span>
                <div>
                  <h3 className="text-sm font-semibold">{point.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-primary-foreground/70">
                    {point.description}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
