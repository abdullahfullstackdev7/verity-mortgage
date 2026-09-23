from __future__ import annotations

import uuid

from sqlalchemy import case as sql_case
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.enums import CaseStatus, DiscrepancySeverity
from backend.app.db.models.user import User
from backend.app.schemas.case import CaseListItem


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


def list_cases_with_details(
    db: Session,
    status: CaseStatus | None,
    page: int,
    size: int,
) -> tuple[list[CaseListItem], int]:
    """Denormalized version of list_cases for the queue table: joins in
    applicant name/loan amount and the assigned underwriter's email, and
    aggregates each case's discrepancy counts, in a constant number of
    queries regardless of page size."""
    cases, total = list_cases(db, status, page, size)
    if not cases:
        return [], total

    case_ids = [c.id for c in cases]
    applicant_ids = {c.applicant_id for c in cases}
    underwriter_ids = {c.assigned_underwriter_id for c in cases if c.assigned_underwriter_id}

    applicants_by_id = {
        a.id: a
        for a in db.execute(select(Applicant).where(Applicant.id.in_(applicant_ids))).scalars()
    }

    underwriter_emails_by_id: dict[uuid.UUID, str] = {}
    if underwriter_ids:
        underwriter_emails_by_id = dict(
            db.execute(
                select(User.id, User.email).where(User.id.in_(underwriter_ids))
            ).all()
        )

    discrepancy_counts: dict[uuid.UUID, tuple[int, int]] = {}
    major_count_expr = func.sum(
        sql_case((Discrepancy.severity == DiscrepancySeverity.MAJOR, 1), else_=0)
    )
    rows = db.execute(
        select(Discrepancy.case_id, func.count(), major_count_expr)
        .where(Discrepancy.case_id.in_(case_ids))
        .group_by(Discrepancy.case_id)
    ).all()
    for case_id, total_count, major_count in rows:
        discrepancy_counts[case_id] = (total_count, major_count)

    items = []
    for c in cases:
        applicant = applicants_by_id.get(c.applicant_id)
        total_count, major_count = discrepancy_counts.get(c.id, (0, 0))
        items.append(
            CaseListItem(
                id=c.id,
                applicant_id=c.applicant_id,
                applicant_name=applicant.name if applicant else "Unknown applicant",
                stated_loan_amount=float(applicant.stated_loan_amount) if applicant else 0.0,
                status=c.status,
                discrepancy_count=total_count,
                major_discrepancy_count=major_count,
                assigned_underwriter_email=(
                    underwriter_emails_by_id.get(c.assigned_underwriter_id)
                    if c.assigned_underwriter_id
                    else None
                ),
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return items, total
