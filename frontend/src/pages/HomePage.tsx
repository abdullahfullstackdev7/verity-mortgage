import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import { HeroIllustration } from '@/components/marketing/HeroIllustration'
import { MetricsBar } from '@/components/marketing/MetricsBar'
import { SecurityCallout } from '@/components/marketing/SecurityCallout'
import { SectionHeading } from '@/components/marketing/SectionHeading'
import { WorkflowSteps } from '@/components/marketing/WorkflowSteps'
import { Button } from '@/components/ui/button'

export function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-20 sm:py-28 lg:grid-cols-2 lg:py-32">
        <div>
          <p className="text-sm font-semibold tracking-wide text-accent uppercase">
            Underwriting Automation
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            Underwriting decisions in minutes, not days.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
            Verity ingests a loan applicant&apos;s document packet, cross-verifies every figure
            against the application, and delivers an underwriter-ready summary with a routing
            recommendation -- backed by an auditable decision trail from the first upload to the
            final call.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Button size="lg" nativeButton={false} render={<Link to="/contact" />}>
              Request a Demo
              <ArrowRight className="size-4" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              nativeButton={false}
              render={<Link to="/how-it-works" />}
            >
              See how it works
            </Button>
          </div>
        </div>
        <div className="flex justify-center lg:justify-end">
          <HeroIllustration />
        </div>
      </section>

      {/* Metrics / trust bar */}
      <section className="mx-auto max-w-6xl px-6 pb-20">
        <MetricsBar />
      </section>

      {/* Workflow */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <SectionHeading
          eyebrow="The Pipeline"
          title="From intake to decision in four steps"
          description="Every case moves through the same disciplined pipeline, whether it sails through clean or needs a closer look."
        />
        <div className="mt-16">
          <WorkflowSteps />
        </div>
      </section>

      {/* Security callout */}
      <section className="mx-auto max-w-6xl px-6 py-8 pb-24">
        <SecurityCallout />
      </section>
    </>
  )
}
