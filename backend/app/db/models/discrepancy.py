from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.db.models.enums import DiscrepancySeverity

if TYPE_CHECKING:
    from backend.app.db.models.case import Case
    from backend.app.db.models.document import Document


class Discrepancy(Base):
    __tablename__ = "discrepancies"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stated_value: Mapped[str] = mapped_column(String(255), nullable=False)
    document_value: Mapped[str] = mapped_column(String(255), nullable=False)
    variance_pct: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    severity: Mapped[DiscrepancySeverity] = mapped_column(
        SAEnum(DiscrepancySeverity, name="discrepancy_severity", native_enum=True), nullable=False
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )

    case: Mapped[Case] = relationship(back_populates="discrepancies")
    source_document: Mapped[Document | None] = relationship()
