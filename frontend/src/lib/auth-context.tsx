import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { ApiError, getMe, login as apiLogin, logout as apiLogout, tokenStorage } from './api'
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
      if (!tokenStorage.getAccessToken() && !tokenStorage.getRefreshToken()) {
        if (!cancelled) setStatus('unauthenticated')
        return
      }
      try {
        const me = await getMe()
        if (!cancelled) {
          setUser(me)
          setStatus('authenticated')
        }
      } catch {
        tokenStorage.clear()
        if (!cancelled) setStatus('unauthenticated')
      }
    }

    void restoreSession()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiLogin(email, password)
    tokenStorage.setTokens(tokens.access_token, tokens.refresh_token)
    try {
      const me = await getMe()
      setUser(me)
      setStatus('authenticated')
    } catch (error) {
      tokenStorage.clear()
      throw error
    }
  }, [])

  const logout = useCallback(async () => {
    const refreshToken = tokenStorage.getRefreshToken()
    tokenStorage.clear()
    setUser(null)
    setStatus('unauthenticated')
    if (refreshToken) {
      try {
        await apiLogout(refreshToken)
      } catch {
        // best-effort server-side revocation; the client already cleared its tokens
      }
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
