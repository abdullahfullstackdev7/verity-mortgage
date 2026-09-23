import type {
  Applicant,
  AuditLogEntry,
  Case,
  CaseListItem,
  CaseStatus,
  CaseSummary,
  Discrepancy,
  DocumentRecord,
  DocumentType,
  ExtractedField,
  Page,
  User,
} from './types'

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api/v1'

// Token storage: plain localStorage for now. The plan's preference for
// httpOnly cookies requires the backend to set them on login/refresh
// (Set-Cookie), which is Phase 11's hardening work, not built yet -- so
// this is the pragmatic SPA-JWT approach until that lands.
const ACCESS_TOKEN_KEY = 'verity.access_token'
const REFRESH_TOKEN_KEY = 'verity.refresh_token'

export const tokenStorage = {
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens(accessToken: string, refreshToken: string) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  },
  clear() {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}

export class ApiError extends Error {
  status: number
  errorCode: string | undefined
  detail: unknown

  constructor(status: number, errorCode: string | undefined, detail: unknown) {
    const message =
      typeof detail === 'string' ? detail : (errorCode ?? `Request failed with status ${status}`)
    super(message)
    this.status = status
    this.errorCode = errorCode
    this.detail = detail
  }
}

let refreshPromise: Promise<boolean> | null = null

async function refreshTokens(): Promise<boolean> {
  const refreshToken = tokenStorage.getRefreshToken()
  if (!refreshToken) return false

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!response.ok) {
    tokenStorage.clear()
    return false
  }
  const body = (await response.json()) as { access_token: string; refresh_token: string }
  tokenStorage.setTokens(body.access_token, body.refresh_token)
  return true
}

interface RequestOptions {
  method?: string
  params?: Record<string, string | number | boolean | undefined>
  json?: unknown
  formData?: FormData
  skipAuth?: boolean
  raw?: boolean
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`)
  if (options.params) {
    for (const [key, value] of Object.entries(options.params)) {
      if (value !== undefined) url.searchParams.set(key, String(value))
    }
  }

  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = {}
    if (options.json !== undefined) headers['Content-Type'] = 'application/json'

    if (!options.skipAuth) {
      const token = tokenStorage.getAccessToken()
      if (token) headers.Authorization = `Bearer ${token}`
    }

    return fetch(url.toString(), {
      method: options.method ?? 'GET',
      headers,
      body: options.formData ?? (options.json !== undefined ? JSON.stringify(options.json) : undefined),
    })
  }

  let response = await doFetch()

  if (response.status === 401 && !options.skipAuth && tokenStorage.getRefreshToken()) {
    refreshPromise ??= refreshTokens().finally(() => {
      refreshPromise = null
    })
    const refreshed = await refreshPromise
    if (refreshed) {
      response = await doFetch()
    }
  }

  if (!response.ok) {
    let errorCode: string | undefined
    let detail: unknown = response.statusText
    try {
      const body = await response.json()
      errorCode = body.error_code
      detail = body.detail ?? detail
    } catch {
      // response wasn't JSON; keep the status text as the detail
    }
    throw new ApiError(response.status, errorCode, detail)
  }

  if (options.raw || response.status === 204) return undefined as T
  return (await response.json()) as T
}

// --- Auth ---

export function login(email: string, password: string) {
  return request<{ access_token: string; refresh_token: string; token_type: string }>(
    '/auth/login',
    { method: 'POST', json: { email, password }, skipAuth: true },
  )
}

export function logout(refreshToken: string) {
  return request<void>('/auth/logout', {
    method: 'POST',
    json: { refresh_token: refreshToken },
    skipAuth: true,
  })
}

export function getMe() {
  return request<User>('/users/me')
}

// --- Users (admin) ---

export function listUsers() {
  return request<User[]>('/users')
}

export function createUser(email: string, password: string, role: string) {
  return request<User>('/users', { method: 'POST', json: { email, password, role } })
}

// --- Applicants ---

export function listApplicants(search?: string, page = 1, size = 20) {
  return request<Page<Applicant>>('/applicants', { params: { search, page, size } })
}

export function getApplicant(applicantId: string) {
  return request<Applicant>(`/applicants/${applicantId}`)
}

// --- Cases ---

export function listCases(status?: CaseStatus, page = 1, size = 50) {
  return request<Page<CaseListItem>>('/cases', { params: { status, page, size } })
}

export function getCase(caseId: string) {
  return request<Case>(`/cases/${caseId}`)
}

export function createCase(applicantId: string) {
  return request<Case>('/cases', { method: 'POST', json: { applicant_id: applicantId } })
}

export function submitForReview(caseId: string) {
  return request<Case>(`/cases/${caseId}/submit-for-review`, { method: 'POST' })
}

export function routeCase(caseId: string) {
  return request<Case>(`/cases/${caseId}/route`, { method: 'POST' })
}

export function decideCase(caseId: string, decision: string, overrideReason: string | null) {
  return request<Case>(`/cases/${caseId}/decision`, {
    method: 'POST',
    json: { decision, override_reason: overrideReason },
  })
}

export function listAuditLog(caseId: string) {
  return request<AuditLogEntry[]>(`/cases/${caseId}/audit-log`)
}

export function verifyCase(caseId: string, force = false) {
  return request<Discrepancy[]>(`/cases/${caseId}/verify`, { method: 'POST', params: { force } })
}

export function listDiscrepancies(caseId: string) {
  return request<Discrepancy[]>(`/cases/${caseId}/discrepancies`)
}

export function generateSummary(caseId: string, force = false) {
  return request<CaseSummary>(`/cases/${caseId}/summary`, { method: 'POST', params: { force } })
}

export async function getSummary(caseId: string): Promise<CaseSummary | null> {
  try {
    return await request<CaseSummary>(`/cases/${caseId}/summary`)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

// --- Documents ---

export function listDocuments(caseId: string) {
  return request<DocumentRecord[]>(`/cases/${caseId}/documents`)
}

export function uploadDocument(caseId: string, docType: DocumentType, file: File) {
  const formData = new FormData()
  formData.append('doc_type', docType)
  formData.append('file', file)
  return request<DocumentRecord>(`/cases/${caseId}/documents`, { method: 'POST', formData })
}

export function extractDocument(caseId: string, documentId: string, force = false) {
  return request<ExtractedField[]>(`/cases/${caseId}/documents/${documentId}/extract`, {
    method: 'POST',
    params: { force },
  })
}

export function listExtractedFields(caseId: string, documentId: string) {
  return request<ExtractedField[]>(`/cases/${caseId}/documents/${documentId}/fields`)
}

export async function fetchDocumentFileUrl(caseId: string, documentId: string): Promise<string> {
  const token = tokenStorage.getAccessToken()
  const response = await fetch(
    `${API_BASE_URL}/cases/${caseId}/documents/${documentId}/file`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  )
  if (!response.ok) throw new ApiError(response.status, undefined, 'Failed to load document')
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}
