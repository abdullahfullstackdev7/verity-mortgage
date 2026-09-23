const METRICS = [
  { value: '4', label: 'Verification checks run automatically per case' },
  { value: '<2 min', label: 'Typical time from upload to a routed decision' },
  { value: '100%', label: 'Of decisions backed by a written audit trail' },
  { value: '2', label: 'Independent AI providers, so a narrative is never blocked' },
]

export function MetricsBar() {
  return (
    <div className="rounded-2xl border border-border bg-card px-8 py-10 shadow-sm">
      <dl className="grid grid-cols-2 gap-y-10 sm:grid-cols-4 sm:gap-y-0">
        {METRICS.map((metric) => (
          <div key={metric.label} className="text-center sm:border-l sm:border-border sm:px-6 sm:first:border-l-0">
            <dt className="sr-only">{metric.label}</dt>
            <dd className="font-heading text-3xl font-semibold text-primary sm:text-4xl">
              {metric.value}
            </dd>
            <dd className="mt-2 text-sm leading-snug text-muted-foreground">{metric.label}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
