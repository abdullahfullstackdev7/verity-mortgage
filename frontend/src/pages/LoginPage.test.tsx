import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LoginPage } from './LoginPage'
import { ApiError } from '@/lib/api'
import * as authContext from '@/lib/auth-context'

vi.mock('@/lib/auth-context', async () => {
  const actual = await vi.importActual<typeof import('@/lib/auth-context')>('@/lib/auth-context')
  return {
    ...actual,
    useAuth: vi.fn(),
  }
})

const mockedUseAuth = vi.mocked(authContext.useAuth)

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    mockedUseAuth.mockReset()
  })

  it('submits the entered credentials to login', async () => {
    const user = userEvent.setup()
    const login = vi.fn().mockResolvedValue(undefined)
    mockedUseAuth.mockReturnValue({ user: null, status: 'unauthenticated', login, logout: vi.fn() })

    renderLoginPage()
    await user.type(screen.getByLabelText(/work email/i), 'underwriter@verity.test')
    await user.type(screen.getByLabelText(/password/i), 'correct-horse-battery-staple')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(login).toHaveBeenCalledWith('underwriter@verity.test', 'correct-horse-battery-staple')
  })

  it('shows an incorrect-credentials message on a 401', async () => {
    const user = userEvent.setup()
    const login = vi.fn().mockRejectedValue(new ApiError(401, 'unauthorized', 'Incorrect email or password'))
    mockedUseAuth.mockReturnValue({ user: null, status: 'unauthenticated', login, logout: vi.fn() })

    renderLoginPage()
    await user.type(screen.getByLabelText(/work email/i), 'underwriter@verity.test')
    await user.type(screen.getByLabelText(/password/i), 'wrong-password')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/incorrect email or password/i)
  })

  it('shows a generic error message on a non-401 failure', async () => {
    const user = userEvent.setup()
    const login = vi.fn().mockRejectedValue(new Error('network down'))
    mockedUseAuth.mockReturnValue({ user: null, status: 'unauthenticated', login, logout: vi.fn() })

    renderLoginPage()
    await user.type(screen.getByLabelText(/work email/i), 'underwriter@verity.test')
    await user.type(screen.getByLabelText(/password/i), 'correct-horse-battery-staple')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong signing you in/i)
  })
})
