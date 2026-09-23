from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.app.db.models.enums import UserRole

_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    role: UserRole

    @field_validator("password")
    @classmethod
    def _password_complexity(cls, value: str) -> str:
        if not _HAS_LETTER.search(value) or not _HAS_DIGIT.search(value):
            raise ValueError("password must contain at least one letter and one digit")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: UserRole
    created_at: datetime
