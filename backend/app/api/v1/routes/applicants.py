from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.user import User
from backend.app.schemas.applicant import ApplicantRead
from backend.app.schemas.common import Page
from backend.app.services import applicant_service

router = APIRouter(prefix="/applicants", tags=["applicants"])


@router.get("", response_model=Page[ApplicantRead])
def list_applicants(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Page[ApplicantRead]:
    items, total = applicant_service.list_applicants(db, search, page, size)
    pages = math.ceil(total / size) if total else 0
    return Page[ApplicantRead](items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{applicant_id}", response_model=ApplicantRead)
def get_applicant(
    applicant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Applicant:
    applicant = applicant_service.get_applicant(db, applicant_id)
    if applicant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Applicant not found")
    return applicant
