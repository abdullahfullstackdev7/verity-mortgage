from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    address: str
    employer_name: str
    hmda_source_id: str
    stated_income: float
    stated_loan_amount: float
    stated_property_value: float
    stated_dti: float
    created_at: datetime
