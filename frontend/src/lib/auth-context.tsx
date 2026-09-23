import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { ApiError, getMe, login as apiLogin, logout as apiLogout } from './api'
import type { User } from './types'

interface AuthContextValue {
  user: User | null
  status: 'loading' | 'authenticated' | 'unauthenticated'
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthContextValue['status']>('loading')

  useEffect(() => {
    let cancelled = false

    async function restoreSession() {
      // No token to check client-side -- the session lives in an httpOnly
      // cookie the browser sends automatically, so just ask the API
      // whether it recognizes us.
      try {
        const me = await getMe()
        if (!cancelled) {
          setUser(me)
          setStatus('authenticated')
        }
      } catch {
        if (!cancelled) setStatus('unauthenticated')
      }
    }

    void restoreSession()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    await apiLogin(email, password)
    const me = await getMe()
    setUser(me)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(async () => {
    setUser(null)
    setStatus('unauthenticated')
    try {
      await apiLogout()
    } catch {
      // best-effort server-side revocation; the client already cleared its session
    }
  }, [])

  const value = useMemo(() => ({ user, status, login, logout }), [user, status, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
