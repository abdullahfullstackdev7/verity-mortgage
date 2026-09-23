"""Routing rules and the underwriter decision endpoint's logic.

Routing rules (per case, once under_review): no discrepancies at all ->
auto-approve; only minor discrepancies -> auto-refer for human review; any
major discrepancy -> stays under_review, blocked from auto-approval, and
requires a manual underwriter decision.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.db.models.audit_log import AuditLog
from backend.app.db.models.case import Case
from backend.app.db.models.case_summary import CaseSummary
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.enums import CaseStatus, DiscrepancySeverity, Recommendation
from backend.app.services.case_state_machine import (
    GuardNotSatisfiedError,
    TransitionNotAllowedError,
    check_required_documents_extracted,
    check_required_documents_present,
    transition_case,
)

SYSTEM_ACTOR = "system"

DECISION_STATUSES = {CaseStatus.APPROVED, CaseStatus.REFERRED, CaseStatus.DENIED}

# Recommendation and CaseStatus use different word forms for the same
# concept ("approve" vs "approved", etc.), so the two need an explicit
# mapping rather than a raw string comparison.
RECOMMENDATION_TO_STATUS: dict[Recommendation, CaseStatus] = {
    Recommendation.APPROVE: CaseStatus.APPROVED,
    Recommendation.REFER: CaseStatus.REFERRED,
    Recommendation.DENY: CaseStatus.DENIED,
}


class DecisionError(Exception):
    pass


def submit_for_review(db: Session, case: Case, actor: str) -> Case:
    """Loan-officer action: move a case from submitted/documents_pending
    into under_review, once all required documents are present."""
    if case.status not in (CaseStatus.SUBMITTED, CaseStatus.DOCUMENTS_PENDING):
        raise TransitionNotAllowedError(
            f"Case must be submitted or documents_pending to submit for review "
            f"(current status: {case.status.value})"
        )

    ok, reason = check_required_documents_present(db, case)
    if not ok:
        raise GuardNotSatisfiedError(reason)

    if case.status == CaseStatus.SUBMITTED:
        case = transition_case(
            db, case, CaseStatus.DOCUMENTS_PENDING, actor, "All required documents uploaded"
        )
    return transition_case(db, case, CaseStatus.UNDER_REVIEW, actor, reason)


def auto_route_case(db: Session, case: Case) -> Case:
    """System action: apply the routing rules to a case that is
    under_review, based on its current discrepancies."""
    if case.status != CaseStatus.UNDER_REVIEW:
        raise TransitionNotAllowedError(
            f"Case must be under_review to auto-route (current status: {case.status.value})"
        )

    ok, reason = check_required_documents_extracted(db, case)
    if not ok:
        raise GuardNotSatisfiedError(reason)

    discrepancies = db.query(Discrepancy).filter(Discrepancy.case_id == case.id).all()
    major = [d for d in discrepancies if d.severity == DiscrepancySeverity.MAJOR]

    if not discrepancies:
        return transition_case(
            db,
            case,
            CaseStatus.APPROVED,
            SYSTEM_ACTOR,
            "No discrepancies found across all verification checks; auto-approved",
        )

    if not major:
        minor_fields = ", ".join(sorted(d.field_name for d in discrepancies))
        return transition_case(
            db,
            case,
            CaseStatus.REFERRED,
            SYSTEM_ACTOR,
            f"Only minor discrepancies found ({minor_fields}); referred for underwriter review",
        )

    major_fields = ", ".join(sorted(d.field_name for d in major))
    db.add(
        AuditLog(
            case_id=case.id,
            actor=SYSTEM_ACTOR,
            action="auto_route_blocked",
            rule_or_evidence=(
                f"Major discrepancy in: {major_fields}; auto-approval blocked, "
                "mandatory manual underwriter decision required"
            ),
        )
    )
    db.commit()
    db.refresh(case)
    return case


def record_underwriter_decision(
    db: Session,
    case: Case,
    decision: CaseStatus,
    override_reason: str | None,
    actor: str,
) -> Case:
    """Underwriter action: accept or override the system's recommendation.
    override_reason is mandatory whenever the decision differs from the
    latest case summary's recommendation (or there is no summary yet)."""
    if decision not in DECISION_STATUSES:
        raise ValueError("decision must be one of: approved, referred, denied")

    if case.status not in (CaseStatus.UNDER_REVIEW, CaseStatus.REFERRED):
        raise TransitionNotAllowedError(
            f"Case must be under_review or referred for a decision "
            f"(current status: {case.status.value})"
        )

    latest_summary = (
        db.query(CaseSummary)
        .filter(CaseSummary.case_id == case.id)
        .order_by(CaseSummary.created_at.desc())
        .first()
    )
    system_recommendation = latest_summary.recommendation if latest_summary else None
    recommended_status = (
        RECOMMENDATION_TO_STATUS[system_recommendation] if system_recommendation else None
    )
    is_override = recommended_status is None or recommended_status != decision

    if is_override and not (override_reason and override_reason.strip()):
        raise DecisionError(
            "override_reason is required: the decision differs from the system "
            "recommendation (or no recommendation exists yet)"
        )

    rule_or_evidence = (
        f"Underwriter decision: {decision.value}. "
        f"System recommendation: {system_recommendation.value if system_recommendation else 'none'}. "
        f"Override reason: {override_reason.strip() if override_reason else 'N/A (matches system recommendation)'}"
    )
    return transition_case(db, case, decision, actor, rule_or_evidence)
