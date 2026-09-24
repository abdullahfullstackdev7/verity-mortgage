from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.db.models.policy_chunk import EMBEDDING_DIM

if TYPE_CHECKING:
    from backend.app.db.models.document import Document


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    __table_args__ = (
        # Guards against the extraction pipeline's check-then-insert
        # idempotency logic racing itself under concurrent/rapid re-extract
        # calls on the same document, which would otherwise silently create
        # duplicate rows and break the single-row lookup in the rules engine.
        UniqueConstraint("document_id", "field_name", name="uq_document_embeddings_document_id_field_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)

    document: Mapped[Document] = relationship(back_populates="embeddings")
