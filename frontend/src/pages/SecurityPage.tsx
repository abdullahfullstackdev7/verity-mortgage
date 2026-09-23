import { Database, FileClock, KeyRound, Lock, ShieldAlert, UserCheck } from 'lucide-react'

import { SectionHeading } from '@/components/marketing/SectionHeading'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const PRACTICES = [
  {
    icon: Lock,
    title: 'Encryption in transit and at rest',
    description:
      'All traffic to the platform is encrypted, and stored data is encrypted at the database layer. Secrets and API keys are loaded from environment configuration and are never committed to source control.',
  },
  {
    icon: KeyRound,
    title: 'JWT authentication, short-lived tokens',
    description:
      'Access tokens are short-lived and refresh tokens rotate on every use, with a revocation list so a compromised or logged-out token can’t be replayed.',
  },
  {
    icon: UserCheck,
    title: 'Role-based access control',
    description:
      'Loan officer, underwriter, and admin roles are enforced at the API layer on every protected route -- not just hidden in the interface -- so a role change takes effect everywhere at once.',
  },
  {
    icon: ShieldAlert,
    title: 'Validated input, everywhere',
    description:
      'Every request is validated against a strict schema. Document uploads are checked by file content, not extension, and are rejected outright if they aren’t a genuine PDF.',
  },
  {
    icon: FileClock,
    title: 'Immutable audit logging',
    description:
      'Every case status change -- automatic or manual -- is written to a permanent audit log with its actor and the rule or evidence that produced it, so any decision can be reconstructed later.',
  },
  {
    icon: Database,
    title: 'Built on verifiable, public data',
    description:
      'Our reference and demo environments are seeded from the public HMDA loan dataset. Supporting documents are synthetically generated from those figures -- never a real applicant’s actual financial records.',
  },
]

export function SecurityPage() {
  return (
    <>
      <section className="mx-auto max-w-6xl px-6 py-20 sm:py-24">
        <SectionHeading
          eyebrow="Security & Compliance"
          title="Built for teams that answer to auditors"
          description="Every recommendation the system makes is explainable, and every decision a human makes is recorded. Here's what that looks like in practice."
        />
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-20">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {PRACTICES.map((practice) => {
            const Icon = practice.icon
            return (
              <Card key={practice.title} className="border-border">
                <CardHeader>
                  <span className="flex size-11 items-center justify-center rounded-full bg-secondary">
                    <Icon className="size-5 text-primary" strokeWidth={1.75} />
                  </span>
                  <CardTitle className="mt-4 text-base">{practice.title}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm leading-relaxed text-muted-foreground">
                  {practice.description}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-6 pb-24">
        <div className="rounded-2xl border border-border bg-secondary/40 p-8">
          <h3 className="text-lg font-semibold text-foreground">A note on this environment</h3>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            This is a reference implementation, not a production financial institution. Applicant
            figures come from the public HMDA Modified Loan Application Register; supporting
            documents (pay stubs, bank statements, W-2s) are synthetically generated from those
            figures using Faker and template rendering. No real applicant, employer, or financial
            document appears anywhere in this system.
          </p>
        </div>
      </section>
    </>
  )
}
