from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.db.models.applicant import Applicant


def get_applicant(db: Session, applicant_id: uuid.UUID) -> Applicant | None:
    return db.get(Applicant, applicant_id)


def list_applicants(
    db: Session,
    search: str | None,
    page: int,
    size: int,
) -> tuple[list[Applicant], int]:
    """List applicants (the demo/HMDA-seeded pool loan officers pick from
    when creating a case), optionally filtered by a case-insensitive
    substring match on name or employer name."""
    query = select(Applicant)
    count_query = select(func.count()).select_from(Applicant)

    if search:
        pattern = f"%{search}%"
        condition = or_(Applicant.name.ilike(pattern), Applicant.employer_name.ilike(pattern))
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = db.execute(count_query).scalar_one()
    items = (
        db.execute(
            query.order_by(Applicant.name).offset((page - 1) * size).limit(size)
        )
        .scalars()
        .all()
    )
    return list(items), total
