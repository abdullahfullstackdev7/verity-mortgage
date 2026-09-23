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

// Session storage: httpOnly cookies, set by the backend on login/refresh
// (see backend/app/core/cookies.py). The app never reads or stores a
// token in JS-accessible memory or localStorage -- every request just
// sends `credentials: 'include'` and lets the browser attach the cookie,
// so an XSS payload on this page has nothing to steal. The backend also
// still returns the tokens in the JSON body for non-browser/API clients;
// this app deliberately ignores that field.

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
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  })
  return response.ok
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

    return fetch(url.toString(), {
      method: options.method ?? 'GET',
      headers,
      credentials: 'include',
      body: options.formData ?? (options.json !== undefined ? JSON.stringify(options.json) : undefined),
    })
  }

  let response = await doFetch()

  if (response.status === 401 && !options.skipAuth) {
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
  // The session actually lives in the httpOnly cookie the backend just
  // set on this response; the JSON body's tokens (kept for non-browser
  // API clients) are intentionally never read here.
  return request<{ access_token: string; refresh_token: string; token_type: string }>(
    '/auth/login',
    { method: 'POST', json: { email, password }, skipAuth: true },
  )
}

export function logout() {
  return request<void>('/auth/logout', { method: 'POST', skipAuth: true })
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
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/documents/${documentId}/file`, {
    credentials: 'include',
  })
  if (!response.ok) throw new ApiError(response.status, undefined, 'Failed to load document')
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}
