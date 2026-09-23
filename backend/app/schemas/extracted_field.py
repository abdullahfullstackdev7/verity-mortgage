from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class ExtractedFieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    field_name: str
    extracted_value: str
    confidence_score: float | None
    raw_text_snippet: str | None
