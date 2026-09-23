from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class DecisionRequest(BaseModel):
    decision: Literal["approved", "referred", "denied"]
    override_reason: str | None = None
