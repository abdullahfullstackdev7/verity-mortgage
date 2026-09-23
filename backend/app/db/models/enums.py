import enum


class UserRole(str, enum.Enum):
    LOAN_OFFICER = "loan_officer"
    UNDERWRITER = "underwriter"
    ADMIN = "admin"


class CaseStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    DOCUMENTS_PENDING = "documents_pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REFERRED = "referred"
    DENIED = "denied"


class DocumentType(str, enum.Enum):
    PAYSTUB = "paystub"
    BANK_STATEMENT = "bank_statement"
    W2 = "w2"
    ID = "id"


class OcrStatus(str, enum.Enum):
    PENDING_OCR = "pending_ocr"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscrepancySeverity(str, enum.Enum):
    MINOR = "minor"
    MAJOR = "major"


class Recommendation(str, enum.Enum):
    APPROVE = "approve"
    REFER = "refer"
    DENY = "deny"
