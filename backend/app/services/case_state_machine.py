"""Explicit case status transition table with guarded transitions, plus the
audit_log write every transition is required to produce.

    submitted -> documents_pending -> under_review -> approved | referred | denied
                                                     -> (referred can still be finalized: approved | denied)

An explicit transition table (rather than a state-machine library) keeps
this dependency-free and makes every allowed edge and its guard visible in
one place.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.db.models.audit_log import AuditLog
from backend.app.db.models.case import Case
from backend.app.db.models.document import Document
from backend.app.db.models.enums import CaseStatus, DocumentType, OcrStatus

# The intake documents the extraction/verification pipeline (Phases 5-6)
# actually processes. An "ID" document type exists in the schema for future
# use but isn't extracted or verified anywhere yet, so it isn't required here.
REQUIRED_DOCUMENT_TYPES: set[DocumentType] = {
    DocumentType.PAYSTUB,
    DocumentType.BANK_STATEMENT,
    DocumentType.W2,
}

ALLOWED_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.SUBMITTED: {CaseStatus.DOCUMENTS_PENDING},
    CaseStatus.DOCUMENTS_PENDING: {CaseStatus.UNDER_REVIEW},
    CaseStatus.UNDER_REVIEW: {CaseStatus.APPROVED, CaseStatus.REFERRED, CaseStatus.DENIED},
    CaseStatus.REFERRED: {CaseStatus.APPROVED, CaseStatus.DENIED},
    CaseStatus.APPROVED: set(),
    CaseStatus.DENIED: set(),
}


class TransitionNotAllowedError(Exception):
    pass


class GuardNotSatisfiedError(Exception):
    pass


def can_transition(current: CaseStatus, target: CaseStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def check_required_documents_present(db: Session, case: Case) -> tuple[bool, str]:
    present_types = {
        row[0] for row in db.query(Document.doc_type).filter(Document.case_id == case.id).all()
    }
    missing = REQUIRED_DOCUMENT_TYPES - present_types
    if missing:
        missing_names = ", ".join(sorted(t.value for t in missing))
        return False, f"Missing required documents: {missing_names}"
    return True, "All required documents are present"


def check_required_documents_extracted(db: Session, case: Case) -> tuple[bool, str]:
    """Guard for auto-routing: a case with zero discrepancies only means
    "clean" if its documents were actually extracted. Without this, a case
    whose documents were never processed would look indistinguishable from
    a genuinely clean one and get auto-approved by default."""
    completed_types = {
        row[0]
        for row in db.query(Document.doc_type)
        .filter(Document.case_id == case.id, Document.ocr_status == OcrStatus.COMPLETED)
        .all()
    }
    missing = REQUIRED_DOCUMENT_TYPES - completed_types
    if missing:
        missing_names = ", ".join(sorted(t.value for t in missing))
        return False, f"Required documents not yet extracted: {missing_names}"
    return True, "All required documents have been extracted"


def transition_case(
    db: Session,
    case: Case,
    target_status: CaseStatus,
    actor: str,
    rule_or_evidence: str,
) -> Case:
    """Apply a guarded status transition and write its audit_log entry.
    Raises TransitionNotAllowedError if the edge isn't in the transition
    table; callers are responsible for checking any guard condition first."""
    if not can_transition(case.status, target_status):
        raise TransitionNotAllowedError(
            f"Cannot transition case from {case.status.value} to {target_status.value}"
        )

    case.status = target_status
    db.add(
        AuditLog(
            case_id=case.id,
            actor=actor,
            action=f"status_changed_to_{target_status.value}",
            rule_or_evidence=rule_or_evidence,
        )
    )
    db.commit()
    db.refresh(case)
    return case
