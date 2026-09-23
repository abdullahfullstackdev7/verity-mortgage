from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.enums import CaseStatus


class ApplicantNotFoundError(Exception):
    pass


def create_case(db: Session, applicant_id: uuid.UUID) -> Case:
    if db.get(Applicant, applicant_id) is None:
        raise ApplicantNotFoundError(f"No applicant with id {applicant_id}")

    case = Case(applicant_id=applicant_id, status=CaseStatus.SUBMITTED)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def get_case(db: Session, case_id: uuid.UUID) -> Case | None:
    return db.get(Case, case_id)


def list_cases(
    db: Session,
    status: CaseStatus | None,
    page: int,
    size: int,
) -> tuple[list[Case], int]:
    query = select(Case)
    count_query = select(func.count()).select_from(Case)
    if status is not None:
        query = query.where(Case.status == status)
        count_query = count_query.where(Case.status == status)

    total = db.execute(count_query).scalar_one()
    items = (
        db.execute(
            query.order_by(Case.created_at.desc()).offset((page - 1) * size).limit(size)
        )
        .scalars()
        .all()
    )
    return list(items), total


def update_status(db: Session, case: Case, new_status: CaseStatus) -> Case:
    case.status = new_status
    db.commit()
    db.refresh(case)
    return case
