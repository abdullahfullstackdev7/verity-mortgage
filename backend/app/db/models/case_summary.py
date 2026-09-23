from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.db.models.enums import Recommendation

if TYPE_CHECKING:
    from backend.app.db.models.case import Case


class CaseSummary(Base):
    __tablename__ = "case_summaries"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True
    )
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[Recommendation] = mapped_column(
        SAEnum(Recommendation, name="recommendation", native_enum=True), nullable=False
    )
    generated_by_model: Mapped[str] = mapped_column(String(100), nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    case: Mapped["Case"] = relationship(back_populates="summaries")
