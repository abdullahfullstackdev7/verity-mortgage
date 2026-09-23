from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from backend.app.db.models.enums import DiscrepancySeverity


class DiscrepancyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    field_name: str
    stated_value: str
    document_value: str
    variance_pct: float
    severity: DiscrepancySeverity
    source_document_id: uuid.UUID | None
