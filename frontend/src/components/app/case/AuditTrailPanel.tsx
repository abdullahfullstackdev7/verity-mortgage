import { History } from 'lucide-react'

import type { AuditLogEntry } from '@/lib/types'

export function AuditTrailPanel({ entries }: { entries: AuditLogEntry[] }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-center gap-2">
        <History className="size-4 text-muted-foreground" strokeWidth={1.75} />
        <h2 className="text-lg font-semibold text-foreground">Audit Trail</h2>
      </div>

      {entries.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">No activity recorded yet.</p>
      ) : (
        <ol className="mt-4 space-y-4 border-l border-border pl-4">
          {entries.map((entry) => (
            <li key={entry.id} className="relative">
              <span className="absolute -left-[21px] top-1 size-2.5 rounded-full bg-accent" />
              <p className="text-sm font-medium text-foreground">
                {entry.action.replace(/_/g, ' ')}
              </p>
              <p className="text-xs text-muted-foreground">
                {entry.actor} &middot; {new Date(entry.created_at).toLocaleString()}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{entry.rule_or_evidence}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
