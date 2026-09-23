from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.db.models.enums import CaseStatus

if TYPE_CHECKING:
    from backend.app.db.models.applicant import Applicant
    from backend.app.db.models.audit_log import AuditLog
    from backend.app.db.models.case_summary import CaseSummary
    from backend.app.db.models.discrepancy import Discrepancy
    from backend.app.db.models.document import Document
    from backend.app.db.models.user import User


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("applicants.id"), nullable=False, index=True
    )
    status: Mapped[CaseStatus] = mapped_column(
        SAEnum(CaseStatus, name="case_status", native_enum=True),
        nullable=False,
        default=CaseStatus.SUBMITTED,
    )
    assigned_underwriter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    applicant: Mapped["Applicant"] = relationship(back_populates="cases")
    assigned_underwriter: Mapped[Optional["User"]] = relationship()
    documents: Mapped[list["Document"]] = relationship(back_populates="case")
    discrepancies: Mapped[list["Discrepancy"]] = relationship(back_populates="case")
    summaries: Mapped[list["CaseSummary"]] = relationship(back_populates="case")
    audit_entries: Mapped[list["AuditLog"]] = relationship(back_populates="case")
