import { type FormEvent, useEffect, useState } from 'react'
import { UserPlus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ApiError, createUser, listUsers } from '@/lib/api'
import type { User, UserRole } from '@/lib/types'

const ROLE_LABELS: Record<UserRole, string> = {
  loan_officer: 'Loan Officer',
  underwriter: 'Underwriter',
  admin: 'Admin',
}

export function UsersAdminPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('loan_officer')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  function refresh() {
    setLoading(true)
    listUsers()
      .then(setUsers)
      .finally(() => setLoading(false))
  }

  useEffect(refresh, [])

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCreating(true)
    setCreateError(null)
    try {
      await createUser(email, password, role)
      setEmail('')
      setPassword('')
      refresh()
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setCreateError('A user with that email already exists.')
      } else if (err instanceof ApiError && err.status === 422 && Array.isArray(err.detail)) {
        const messages = err.detail
          .map((issue) => (issue as { msg?: string }).msg)
          .filter((msg): msg is string => Boolean(msg))
        setCreateError(messages.join(' ') || 'Could not create user: invalid input.')
      } else {
        setCreateError('Could not create user.')
      }
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl font-semibold text-foreground">Users</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Accounts are admin-created only -- there is no public sign-up.
      </p>

      <form
        onSubmit={handleCreate}
        className="mt-6 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-card p-6"
      >
        <div className="space-y-1.5">
          <Label htmlFor="new-user-email">Email</Label>
          <Input
            id="new-user-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="new-user-password">Password</Label>
          <Input
            id="new-user-password"
            type="password"
            required
            minLength={10}
            placeholder="At least 10 characters, with a letter and a digit"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Role</Label>
          <Select value={role} onValueChange={(v) => setRole(v as UserRole)}>
            <SelectTrigger className="w-40">
              <SelectValue>{(value: UserRole) => ROLE_LABELS[value]}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="loan_officer">Loan Officer</SelectItem>
              <SelectItem value="underwriter">Underwriter</SelectItem>
              <SelectItem value="admin">Admin</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button type="submit" disabled={creating}>
          <UserPlus className="size-4" />
          {creating ? 'Creating…' : 'Create User'}
        </Button>
      </form>
      {createError ? <p className="mt-2 text-sm text-destructive">{createError}</p> : null}

      <div className="mt-6 overflow-hidden rounded-xl border border-border bg-card">
        {loading ? (
          <p className="p-8 text-center text-sm text-muted-foreground">Loading users…</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium text-foreground">{u.email}</TableCell>
                  <TableCell>{ROLE_LABELS[u.role]}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(u.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  )
}
