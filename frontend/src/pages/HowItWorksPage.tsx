import { WorkflowStepDetail } from '@/components/marketing/WorkflowSteps'
import { SectionHeading } from '@/components/marketing/SectionHeading'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

const FAQS = [
  {
    question: 'What happens if OCR can’t read a field confidently?',
    answer:
      'Deterministic extraction runs first and scores its own confidence per field. Only fields that come back missing or below the confidence threshold are sent -- as text, never the document image -- to a language model as a fallback, and that response is validated against a strict schema before it’s trusted.',
  },
  {
    question: 'Can the system approve a loan on its own?',
    answer:
      'Only when every check comes back clean. The moment any check finds a major discrepancy, auto-approval is blocked outright and the case is held for a human underwriter -- there’s no override for that rule.',
  },
  {
    question: 'What does the audit trail actually capture?',
    answer:
      'Every status change, whether triggered automatically by the routing rules or manually by an underwriter, is written as its own entry: who or what triggered it, and the specific rule or evidence behind the call.',
  },
  {
    question: 'What data powers the demo environment?',
    answer:
      'Applicant figures come from the public HMDA loan dataset. Supporting documents -- pay stubs, bank statements, W-2s -- are synthetically generated from those figures, since real applicant financial documents can’t legally be used for a demo.',
  },
]

export function HowItWorksPage() {
  return (
    <>
      <section className="mx-auto max-w-6xl px-6 py-20 sm:py-24">
        <SectionHeading
          eyebrow="How It Works"
          title="A disciplined path from upload to decision"
          description="Four stages, the same evidence trail every time -- whether a case sails through clean or needs a closer look."
        />
      </section>

      <section className="mx-auto max-w-4xl px-6 pb-24">
        <WorkflowStepDetail />
      </section>

      <section className="bg-secondary/40 py-24">
        <div className="mx-auto max-w-3xl px-6">
          <SectionHeading eyebrow="Questions" title="Frequently asked" align="center" />
          <Accordion defaultValue={[]} className="mt-12">
            {FAQS.map((faq, index) => (
              <AccordionItem key={faq.question} value={index}>
                <AccordionTrigger className="text-left text-base font-medium">
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent className="text-sm leading-relaxed text-muted-foreground">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>
    </>
  )
}
