import { Link } from 'react-router-dom'

const FOOTER_COLUMNS: { heading: string; links: { label: string; to: string }[] }[] = [
  {
    heading: 'Product',
    links: [
      { label: 'Solutions', to: '/solutions' },
      { label: 'How It Works', to: '/how-it-works' },
      { label: 'Security & Compliance', to: '/security' },
    ],
  },
  {
    heading: 'Company',
    links: [
      { label: 'About', to: '/about' },
      { label: 'Contact', to: '/contact' },
    ],
  },
  {
    heading: 'Legal',
    links: [
      { label: 'Privacy Policy', to: '/security' },
      { label: 'Terms of Service', to: '/security' },
    ],
  },
]

export function Footer() {
  return (
    <footer className="border-t border-border bg-secondary/40">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-12 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div className="max-w-xs">
            <span className="font-heading text-xl font-semibold tracking-tight text-foreground">
              Verity
            </span>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Intake-to-decision underwriting automation, built on verifiable data and an
              auditable review trail.
            </p>
          </div>

          {FOOTER_COLUMNS.map((column) => (
            <div key={column.heading}>
              <h3 className="text-sm font-semibold text-foreground">{column.heading}</h3>
              <ul className="mt-4 space-y-3">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      to={link.to}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          <div>
            <h3 className="text-sm font-semibold text-foreground">Contact</h3>
            <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
              <li>hello@verity-mortgage.example</li>
              <li>+1 (555) 019-2044</li>
              <li>
                400 Market Street, Suite 900
                <br />
                San Francisco, CA 94105
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-16 flex flex-col gap-4 border-t border-border pt-8 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>&copy; {new Date().getFullYear()} Verity Mortgage. All rights reserved.</p>
          <p>
            Demo environment seeded from public HMDA data with synthetically generated
            supporting documents. No real applicant data is used.
          </p>
        </div>
      </div>
    </footer>
  )
}
