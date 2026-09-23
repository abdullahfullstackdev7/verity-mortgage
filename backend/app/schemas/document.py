from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.db.models.enums import DocumentType, OcrStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    doc_type: DocumentType
    file_path: str
    uploaded_at: datetime
    ocr_status: OcrStatus
