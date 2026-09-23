import { type FormEvent, useState } from 'react'
import { CheckCircle2, Mail, MapPin, Phone } from 'lucide-react'

import { SectionHeading } from '@/components/marketing/SectionHeading'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

const CONTACT_DETAILS = [
  { icon: Mail, label: 'hello@verity-mortgage.example' },
  { icon: Phone, label: '+1 (555) 019-2044' },
  { icon: MapPin, label: '400 Market Street, Suite 900, San Francisco, CA 94105' },
]

export function ContactPage() {
  const [submitted, setSubmitted] = useState(false)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitted(true)
  }

  return (
    <section className="mx-auto grid max-w-6xl gap-16 px-6 py-20 sm:py-24 lg:grid-cols-[1fr_1.1fr]">
      <div>
        <SectionHeading
          eyebrow="Contact"
          title="Talk to our team"
          description="Tell us about your current review process and we'll show you what Verity looks like against your own volume."
        />
        <ul className="mt-10 space-y-5">
          {CONTACT_DETAILS.map((detail) => {
            const Icon = detail.icon
            return (
              <li key={detail.label} className="flex items-center gap-3 text-sm text-muted-foreground">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-secondary">
                  <Icon className="size-4 text-primary" strokeWidth={1.75} />
                </span>
                {detail.label}
              </li>
            )
          })}
        </ul>
      </div>

      <div className="rounded-2xl border border-border bg-card p-8 shadow-sm">
        {submitted ? (
          <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
            <CheckCircle2 className="size-12 text-accent" strokeWidth={1.5} />
            <h3 className="text-xl font-semibold text-foreground">Thanks for reaching out</h3>
            <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
              A member of our team will follow up shortly. In the meantime, feel free to explore
              how the platform works.
            </p>
          </div>
        ) : (
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Full name</Label>
                <Input id="name" name="name" required placeholder="Jordan Blake" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Work email</Label>
                <Input id="email" name="email" type="email" required placeholder="jordan@lender.com" />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="company">Company</Label>
              <Input id="company" name="company" placeholder="Lender or institution name" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="message">How can we help?</Label>
              <Textarea
                id="message"
                name="message"
                required
                rows={5}
                placeholder="Tell us a bit about your current underwriting review process."
              />
            </div>
            <Button type="submit" size="lg" className="w-full sm:w-auto">
              Send message
            </Button>
          </form>
        )}
      </div>
    </section>
  )
}
