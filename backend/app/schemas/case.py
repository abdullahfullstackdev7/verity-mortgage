from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.db.models.enums import CaseStatus


class CaseCreate(BaseModel):
    applicant_id: uuid.UUID


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    applicant_id: uuid.UUID
    status: CaseStatus
    assigned_underwriter_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CaseListItem(BaseModel):
    """Denormalized case row for the queue table -- avoids the frontend
    having to make a separate applicant/discrepancy-count/user lookup per
    row just to render a list."""

    id: uuid.UUID
    applicant_id: uuid.UUID
    applicant_name: str
    stated_loan_amount: float
    status: CaseStatus
    discrepancy_count: int
    major_discrepancy_count: int
    assigned_underwriter_email: str | None
    created_at: datetime
    updated_at: datetime
