from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.db.models.document import Document


class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    __table_args__ = (
        # Same race-condition guard as DocumentEmbedding: prevents concurrent
        # or rapid repeat extraction calls on one document from duplicating
        # its field rows.
        UniqueConstraint("document_id", "field_name", name="uq_extracted_fields_document_id_field_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    extracted_value: Mapped[str] = mapped_column(String(1000), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    raw_text_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[Document] = relationship(back_populates="extracted_fields")
