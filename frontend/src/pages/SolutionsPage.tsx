import {
  BadgeCheck,
  FileSearch,
  Gauge,
  KeyRound,
  Landmark,
  Layers,
  ScanText,
  Sparkles,
} from 'lucide-react'

import { SectionHeading } from '@/components/marketing/SectionHeading'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

const CAPABILITIES = [
  {
    icon: ScanText,
    title: 'Document Intake & OCR',
    description:
      'Loan officers upload pay stubs, bank statements, and W-2s as PDFs, validated by content -- not just file extension -- and queued for extraction automatically.',
  },
  {
    icon: FileSearch,
    title: 'Layout-Aware Extraction',
    description:
      'Deterministic parsing anchored to each document type pulls gross pay, account balances, and wage figures, with a fallback to an LLM only for the fields OCR can’t resolve confidently.',
  },
  {
    icon: Gauge,
    title: 'Cross-Verification Engine',
    description:
      'A pure, tolerance-based rules engine checks income, employer identity, deposit patterns, and debt-to-income ratio against the stated application, every time, the same way.',
  },
  {
    icon: Sparkles,
    title: 'AI-Assisted Summaries',
    description:
      'One compact, single-call summary per case turns flagged discrepancies into a plain-language narrative and a recommendation, grounded in your internal underwriting guidance.',
  },
  {
    icon: Layers,
    title: 'Guarded Decision Routing',
    description:
      'Clean cases can route themselves; anything with a major discrepancy is blocked from auto-approval and requires a human underwriter’s signature.',
  },
  {
    icon: BadgeCheck,
    title: 'Permanent Audit Trail',
    description:
      'Every transition -- automated or manual -- is written to an immutable log with the actor and the specific evidence behind it.',
  },
  {
    icon: KeyRound,
    title: 'Role-Based Access',
    description:
      'Loan officers, underwriters, and admins each get exactly the screens and actions their role calls for -- enforced at the API, not just hidden in the UI.',
  },
  {
    icon: Landmark,
    title: 'Built on Verifiable Data',
    description:
      'Our reference environment is seeded from public HMDA loan data, so every demo case reflects realistic, real-world figures.',
  },
]

const PERSONAS = [
  {
    title: 'For Loan Officers',
    description:
      'Create a case, upload the packet, and submit it for review -- the platform tells you immediately if a required document is missing.',
  },
  {
    title: 'For Underwriters',
    description:
      'Work a queue of cases sorted by what actually needs a human: clean cases are already routed, and every flagged case arrives with the evidence attached.',
  },
  {
    title: 'For Risk & Compliance',
    description:
      'Every decision -- system or human -- is explainable after the fact, with the rule or evidence that produced it a click away.',
  },
]

export function SolutionsPage() {
  return (
    <>
      <section className="mx-auto max-w-6xl px-6 py-20 sm:py-24">
        <SectionHeading
          eyebrow="Solutions"
          title="One platform, from first upload to final decision"
          description="Verity replaces manual document review with a disciplined, auditable pipeline -- without taking the human underwriter out of the loop."
        />
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-24">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((item) => {
            const Icon = item.icon
            return (
              <Card key={item.title} className="border-border">
                <CardHeader>
                  <span className="flex size-11 items-center justify-center rounded-full bg-secondary">
                    <Icon className="size-5 text-primary" strokeWidth={1.75} />
                  </span>
                  <CardTitle className="mt-4 text-base">{item.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-sm leading-relaxed">
                    {item.description}
                  </CardDescription>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>

      <section className="bg-secondary/40 py-24">
        <div className="mx-auto max-w-6xl px-6">
          <SectionHeading
            eyebrow="Built For Your Team"
            title="Every role gets exactly what it needs"
            align="center"
          />
          <div className="mt-14 grid gap-8 sm:grid-cols-3">
            {PERSONAS.map((persona) => (
              <div key={persona.title} className="rounded-2xl border border-border bg-card p-8">
                <h3 className="text-lg font-semibold text-foreground">{persona.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  {persona.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
