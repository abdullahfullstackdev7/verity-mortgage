from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.db.models.case import Case
from backend.app.db.models.enums import CaseStatus, UserRole
from backend.app.db.models.user import User
from backend.app.schemas.case import CaseCreate, CaseRead, CaseStatusUpdate
from backend.app.schemas.common import Page
from backend.app.services import case_service

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


@router.get("", response_model=Page[CaseRead])
def list_cases(
    status_filter: CaseStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Page[CaseRead]:
    items, total = case_service.list_cases(db, status_filter, page, size)
    pages = math.ceil(total / size) if total else 0
    return Page[CaseRead](items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{case_id}", response_model=CaseRead)
def get_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Case:
    return _get_case_or_404(db, case_id)


@router.patch(
    "/{case_id}/status",
    response_model=CaseRead,
    dependencies=[Depends(require_roles(UserRole.UNDERWRITER, UserRole.ADMIN))],
)
def update_case_status(
    case_id: uuid.UUID, body: CaseStatusUpdate, db: Session = Depends(get_db)
) -> Case:
    case = _get_case_or_404(db, case_id)
    return case_service.update_status(db, case, body.status)
