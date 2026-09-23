from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.db.models.enums import Recommendation


class CaseSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    narrative_text: str
    recommendation: Recommendation
    generated_by_model: str
    token_count: int | None
    created_at: datetime
