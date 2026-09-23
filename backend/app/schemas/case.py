from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.db.models.enums import CaseStatus


class CaseCreate(BaseModel):
    applicant_id: uuid.UUID


class CaseStatusUpdate(BaseModel):
    status: CaseStatus


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    applicant_id: uuid.UUID
    status: CaseStatus
    assigned_underwriter_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
