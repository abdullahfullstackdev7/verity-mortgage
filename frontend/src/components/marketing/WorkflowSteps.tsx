import { FileCheck2, ScanText, ShieldCheck, Users } from 'lucide-react'

import { cn } from '@/lib/utils'

const STEPS = [
  {
    icon: FileCheck2,
    title: 'Secure Intake',
    description:
      'Loan officers upload the applicant packet -- pay stub, bank statement, and W-2 -- into an encrypted, role-gated case file.',
  },
  {
    icon: ScanText,
    title: 'Automated Extraction',
    description:
      'OCR and layout-aware parsing pull the figures that matter from every document, with a confidence score on each field.',
  },
  {
    icon: ShieldCheck,
    title: 'Cross-Verification',
    description:
      'A deterministic rules engine checks income, employer identity, deposits, and DTI against the application, and flags anything outside tolerance.',
  },
  {
    icon: Users,
    title: 'Underwriter Decision',
    description:
      'A clean case can route itself; anything flagged goes to a human underwriter, whose decision and reasoning are written to a permanent audit trail.',
  },
]

export function WorkflowSteps({ compact = false }: { compact?: boolean }) {
  return (
    <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
      {STEPS.map((step, index) => {
        const Icon = step.icon
        return (
          <div key={step.title} className="relative">
            {index < STEPS.length - 1 ? (
              <div
                className="absolute top-7 left-[calc(50%+28px)] hidden h-px w-[calc(100%-56px)] bg-border lg:block"
                aria-hidden="true"
              />
            ) : null}
            <div className="relative flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <span className="flex size-14 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Icon className="size-6" strokeWidth={1.75} />
                </span>
                <span className="font-heading text-sm text-muted-foreground">
                  Step {index + 1}
                </span>
              </div>
              <h3 className="text-lg font-semibold text-foreground">{step.title}</h3>
              {!compact ? (
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {step.description}
                </p>
              ) : null}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function WorkflowStepDetail() {
  return (
    <div className={cn('space-y-16')}>
      {STEPS.map((step, index) => {
        const Icon = step.icon
        return (
          <div
            key={step.title}
            className="grid items-start gap-6 rounded-2xl border border-border bg-card p-8 shadow-sm sm:grid-cols-[auto_1fr]"
          >
            <span className="flex size-16 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
              <Icon className="size-7" strokeWidth={1.75} />
            </span>
            <div>
              <p className="text-sm font-semibold text-accent">Step {index + 1}</p>
              <h3 className="mt-1 text-2xl font-semibold text-foreground">{step.title}</h3>
              <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground">
                {step.description}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
