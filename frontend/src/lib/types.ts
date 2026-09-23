export type UserRole = 'loan_officer' | 'underwriter' | 'admin'

export type CaseStatus =
  | 'submitted'
  | 'documents_pending'
  | 'under_review'
  | 'approved'
  | 'referred'
  | 'denied'

export type DocumentType = 'paystub' | 'bank_statement' | 'w2' | 'id'

export type OcrStatus = 'pending_ocr' | 'processing' | 'completed' | 'failed'

export type DiscrepancySeverity = 'minor' | 'major'

export type Recommendation = 'approve' | 'refer' | 'deny'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export interface User {
  id: string
  email: string
  role: UserRole
  created_at: string
}

export interface Applicant {
  id: string
  name: string
  address: string
  employer_name: string
  hmda_source_id: string
  stated_income: number
  stated_loan_amount: number
  stated_property_value: number
  stated_dti: number
  created_at: string
}

export interface CaseListItem {
  id: string
  applicant_id: string
  applicant_name: string
  stated_loan_amount: number
  status: CaseStatus
  discrepancy_count: number
  major_discrepancy_count: number
  assigned_underwriter_email: string | null
  created_at: string
  updated_at: string
}

export interface Case {
  id: string
  applicant_id: string
  status: CaseStatus
  assigned_underwriter_id: string | null
  created_at: string
  updated_at: string
}

export interface DocumentRecord {
  id: string
  case_id: string
  doc_type: DocumentType
  file_path: string
  uploaded_at: string
  ocr_status: OcrStatus
}

export interface ExtractedField {
  id: string
  document_id: string
  field_name: string
  extracted_value: string
  confidence_score: number | null
  raw_text_snippet: string | null
}

export interface Discrepancy {
  id: string
  case_id: string
  field_name: string
  stated_value: string
  document_value: string
  variance_pct: number
  severity: DiscrepancySeverity
  source_document_id: string | null
}

export interface CaseSummary {
  id: string
  case_id: string
  narrative_text: string
  recommendation: Recommendation
  generated_by_model: string
  token_count: number | null
  created_at: string
}

export interface AuditLogEntry {
  id: string
  case_id: string
  actor: string
  action: string
  rule_or_evidence: string
  created_at: string
}
