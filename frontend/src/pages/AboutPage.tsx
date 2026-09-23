import { SectionHeading } from '@/components/marketing/SectionHeading'

const VALUES = [
  {
    title: 'Evidence over instinct',
    description:
      'A recommendation is only worth trusting if you can see exactly why it was made. Every check we run shows its work.',
  },
  {
    title: 'Automation with a human ceiling',
    description:
      'We build the system to move fast on the clean cases so your underwriters can spend their judgment where it actually matters.',
  },
  {
    title: 'Frugal by design',
    description:
      'The rules engine that catches most discrepancies costs nothing to run. Language models are reserved for the one place a narrative genuinely needs one.',
  },
]

export function AboutPage() {
  return (
    <>
      <section className="mx-auto max-w-4xl px-6 py-20 sm:py-24">
        <SectionHeading
          eyebrow="About Verity"
          title="We built the underwriting review we wished existed"
        />
        <div className="mt-8 space-y-6 text-lg leading-relaxed text-muted-foreground">
          <p>
            Mortgage underwriting hasn&apos;t changed as fast as the documents flowing into it.
            Loan officers and underwriters still spend hours a week reading pay stubs line by
            line, checking a number here against a number there, and writing up what they found
            from scratch -- work that doesn&apos;t scale and isn&apos;t consistent from one
            reviewer to the next.
          </p>
          <p>
            Verity automates the parts of that process that are genuinely mechanical --
            extraction, cross-checking, routing -- while leaving the parts that require judgment
            exactly where they belong: with a licensed underwriter. The system never has the
            final word. It just makes sure the person who does has everything they need, already
            organized, the moment they open the case.
          </p>
        </div>
      </section>

      <section className="bg-secondary/40 py-24">
        <div className="mx-auto max-w-6xl px-6">
          <SectionHeading eyebrow="What We Believe" title="Principles behind the platform" align="center" />
          <div className="mt-14 grid gap-8 sm:grid-cols-3">
            {VALUES.map((value) => (
              <div key={value.title} className="rounded-2xl border border-border bg-card p-8">
                <h3 className="text-lg font-semibold text-foreground">{value.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  {value.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
