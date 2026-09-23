import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ProtectedRoute } from './ProtectedRoute'
import * as authContext from '@/lib/auth-context'
import type { User } from '@/lib/types'

vi.mock('@/lib/auth-context', async () => {
  const actual = await vi.importActual<typeof import('@/lib/auth-context')>('@/lib/auth-context')
  return {
    ...actual,
    useAuth: vi.fn(),
  }
})

const mockedUseAuth = vi.mocked(authContext.useAuth)

function makeUser(role: User['role']): User {
  return { id: 'user-1', email: 'u@verity.test', role, created_at: new Date().toISOString() }
}

function renderProtected(roles?: User['role'][]) {
  return render(
    <MemoryRouter initialEntries={['/app/cases']}>
      <Routes>
        <Route path="/login" element={<div>login page</div>} />
        <Route
          path="/app/cases"
          element={
            <ProtectedRoute roles={roles}>
              <div>protected content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    mockedUseAuth.mockReset()
  })

  it('shows a loading state while auth status is loading', () => {
    mockedUseAuth.mockReturnValue({ user: null, status: 'loading', login: vi.fn(), logout: vi.fn() })
    renderProtected()
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('redirects to /login when unauthenticated', () => {
    mockedUseAuth.mockReturnValue({ user: null, status: 'unauthenticated', login: vi.fn(), logout: vi.fn() })
    renderProtected()
    expect(screen.getByText('login page')).toBeInTheDocument()
  })

  it('renders children when authenticated with no role restriction', () => {
    mockedUseAuth.mockReturnValue({
      user: makeUser('underwriter'),
      status: 'authenticated',
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderProtected()
    expect(screen.getByText('protected content')).toBeInTheDocument()
  })

  it('shows a not-authorized message when the role is not allowed', () => {
    mockedUseAuth.mockReturnValue({
      user: makeUser('loan_officer'),
      status: 'authenticated',
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderProtected(['admin'])
    expect(screen.getByText(/not authorized/i)).toBeInTheDocument()
    expect(screen.queryByText('protected content')).not.toBeInTheDocument()
  })

  it('renders children when the role is in the allowed list', () => {
    mockedUseAuth.mockReturnValue({
      user: makeUser('admin'),
      status: 'authenticated',
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderProtected(['admin'])
    expect(screen.getByText('protected content')).toBeInTheDocument()
  })
})
