"""Deterministic Faker-based identity generation for synthetic applicants.

Every field here is fabricated by Faker; none of it is derived from or
resembles a real person. The identity is seeded from the applicant_id so the
same applicant always gets the same name, address, and employer across the
pay stub, bank statement, and W-2 generated for them.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from faker import Faker


@dataclass(frozen=True)
class Identity:
    full_name: str
    address_line: str
    state_abbr: str
    ssn_masked: str
    employee_id: str
    employer_name: str
    employer_ein: str
    employer_address: str
    bank_name: str
    account_number_masked: str
    hire_date: str  # ISO date string


def _seed_for(applicant_id: str, salt: str = "identity") -> int:
    digest = hashlib.sha256(f"{salt}:{applicant_id}".encode()).hexdigest()
    return int(digest[:8], 16)


def build_identity(applicant_id: str) -> Identity:
    fake = Faker()
    fake.seed_instance(_seed_for(applicant_id))

    ssn = fake.ssn()
    ssn_masked = f"XXX-XX-{ssn[-4:]}"

    account_number = fake.bban()
    account_number_masked = f"****{account_number[-4:]}"
    state_abbr = fake.state_abbr()

    return Identity(
        full_name=fake.name(),
        address_line=f"{fake.street_address()}, {fake.city()}, {state_abbr} {fake.zipcode()}",
        state_abbr=state_abbr,
        ssn_masked=ssn_masked,
        employee_id=fake.bothify(text="EMP-######"),
        employer_name=fake.company(),
        employer_ein=fake.numerify(text="##-#######"),
        employer_address=fake.address().replace("\n", ", "),
        bank_name=(
            f"{fake.last_name()} {fake.random_element(['National Bank', 'Federal Credit Union', 'Savings Bank'])}"
        ),
        account_number_masked=account_number_masked,
        hire_date=fake.date_between(start_date="-8y", end_date="-1y").isoformat(),
    )
