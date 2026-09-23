from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.db.models.enums import DocumentType, OcrStatus

if TYPE_CHECKING:
    from backend.app.db.models.case import Case
    from backend.app.db.models.document_embedding import DocumentEmbedding
    from backend.app.db.models.extracted_field import ExtractedField


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True
    )
    doc_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type", native_enum=True), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    ocr_status: Mapped[OcrStatus] = mapped_column(
        SAEnum(OcrStatus, name="ocr_status", native_enum=True),
        nullable=False,
        default=OcrStatus.PENDING_OCR,
    )

    case: Mapped[Case] = relationship(back_populates="documents")
    extracted_fields: Mapped[list[ExtractedField]] = relationship(back_populates="document")
    embeddings: Mapped[list[DocumentEmbedding]] = relationship(back_populates="document")
