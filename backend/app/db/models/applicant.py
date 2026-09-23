from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.db.encrypted_types import EncryptedNumeric

if TYPE_CHECKING:
    from backend.app.db.models.case import Case


class Applicant(Base):
    __tablename__ = "applicants"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    employer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hmda_source_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # Encrypted at rest via pgcrypto (see backend/app/db/encrypted_types.py).
    stated_income: Mapped[float] = mapped_column(EncryptedNumeric(14, 2), nullable=False)
    stated_loan_amount: Mapped[float] = mapped_column(EncryptedNumeric(14, 2), nullable=False)
    stated_property_value: Mapped[float] = mapped_column(EncryptedNumeric(14, 2), nullable=False)
    stated_dti: Mapped[float] = mapped_column(EncryptedNumeric(5, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    cases: Mapped[list[Case]] = relationship(back_populates="applicant")
