from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.db.models.audit_log import AuditLog
from backend.app.db.models.case import Case
from backend.app.db.models.case_summary import CaseSummary
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.enums import CaseStatus, UserRole
from backend.app.db.models.user import User
from backend.app.schemas.audit_log import AuditLogRead
from backend.app.schemas.case import CaseCreate, CaseListItem, CaseRead
from backend.app.schemas.case_summary import CaseSummaryRead
from backend.app.schemas.common import Page
from backend.app.schemas.decision import DecisionRequest
from backend.app.schemas.discrepancy import DiscrepancyRead
from backend.app.services import case_decision_service, case_service
from backend.app.services.case_state_machine import (
    GuardNotSatisfiedError,
    TransitionNotAllowedError,
)
from backend.app.services.rules.engine import run_verification
from backend.app.services.summary.service import (
    SummaryGenerationError,
    generate_case_summary,
)

router = APIRouter(prefix="/cases", tags=["cases"])


def _get_case_or_404(db: Session, case_id: uuid.UUID) -> Case:
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


@router.post(
    "",
    response_model=CaseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.LOAN_OFFICER, UserRole.ADMIN))],
)
def create_case(body: CaseCreate, db: Session = Depends(get_db)) -> Case:
    try:
        return case_service.create_case(db, body.applicant_id)
    except case_service.ApplicantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=Page[CaseListItem])
def list_cases(
    status_filter: CaseStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Page[CaseListItem]:
    items, total = case_service.list_cases_with_details(db, status_filter, page, size)
    pages = math.ceil(total / size) if total else 0
    return Page[CaseListItem](items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{case_id}", response_model=CaseRead)
def get_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Case:
    return _get_case_or_404(db, case_id)


@router.post(
    "/{case_id}/submit-for-review",
    response_model=CaseRead,
    dependencies=[Depends(require_roles(UserRole.LOAN_OFFICER, UserRole.ADMIN))],
)
def submit_case_for_review(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Case:
    case = _get_case_or_404(db, case_id)
    try:
        return case_decision_service.submit_for_review(db, case, actor=current_user.email)
    except GuardNotSatisfiedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TransitionNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/{case_id}/route",
    response_model=CaseRead,
    dependencies=[Depends(require_roles(UserRole.LOAN_OFFICER, UserRole.UNDERWRITER, UserRole.ADMIN))],
)
def route_case(case_id: uuid.UUID, db: Session = Depends(get_db)) -> Case:
    """Apply the automatic routing rules (Phase 8) to a case that is
    under_review: no discrepancies -> approved, minor only -> referred,
    any major discrepancy -> stays under_review for a manual decision."""
    case = _get_case_or_404(db, case_id)
    try:
        return case_decision_service.auto_route_case(db, case)
    except GuardNotSatisfiedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TransitionNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/{case_id}/decision",
    response_model=CaseRead,
    dependencies=[Depends(require_roles(UserRole.UNDERWRITER, UserRole.ADMIN))],
)
def decide_case(
    case_id: uuid.UUID,
    body: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Case:
    case = _get_case_or_404(db, case_id)
    try:
        return case_decision_service.record_underwriter_decision(
            db,
            case,
            CaseStatus(body.decision),
            body.override_reason,
            actor=current_user.email,
        )
    except case_decision_service.DecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TransitionNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{case_id}/audit-log", response_model=list[AuditLogRead])
def list_audit_log(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[AuditLog]:
    case = _get_case_or_404(db, case_id)
    return db.query(AuditLog).filter(AuditLog.case_id == case.id).order_by(AuditLog.created_at).all()


@router.post(
    "/{case_id}/verify",
    response_model=list[DiscrepancyRead],
    dependencies=[Depends(require_roles(UserRole.LOAN_OFFICER, UserRole.UNDERWRITER, UserRole.ADMIN))],
)
def verify_case(case_id: uuid.UUID, force: bool = False, db: Session = Depends(get_db)) -> list[Discrepancy]:
    case = _get_case_or_404(db, case_id)
    return run_verification(db, case, force=force)


@router.get("/{case_id}/discrepancies", response_model=list[DiscrepancyRead])
def list_discrepancies(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[Discrepancy]:
    case = _get_case_or_404(db, case_id)
    return db.query(Discrepancy).filter(Discrepancy.case_id == case.id).all()


@router.post(
    "/{case_id}/summary",
    response_model=CaseSummaryRead,
    dependencies=[Depends(require_roles(UserRole.LOAN_OFFICER, UserRole.UNDERWRITER, UserRole.ADMIN))],
)
def generate_summary(case_id: uuid.UUID, force: bool = False, db: Session = Depends(get_db)) -> CaseSummary:
    case = _get_case_or_404(db, case_id)
    try:
        return generate_case_summary(db, case, force=force)
    except SummaryGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/{case_id}/summary", response_model=CaseSummaryRead)
def get_summary(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> CaseSummary:
    case = _get_case_or_404(db, case_id)
    summary = (
        db.query(CaseSummary).filter(CaseSummary.case_id == case.id).order_by(CaseSummary.created_at.desc()).first()
    )
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No summary generated yet")
    return summary
