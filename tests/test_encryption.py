from __future__ import annotations

import uuid

import pytest
from conftest import requires_db
from sqlalchemy import text

from backend.app.db.base import SessionLocal, engine
from backend.app.db.models.applicant import Applicant

pytestmark = requires_db


@pytest.fixture
def applicant():
    db = SessionLocal()
    a = Applicant(
        id=uuid.uuid4(),
        name="Encryption Test Applicant",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"encryption-test:{uuid.uuid4()}",
        stated_income=123456.78,
        stated_loan_amount=400000.00,
        stated_property_value=450000.00,
        stated_dti=33.25,
    )
    db.add(a)
    db.commit()
    applicant_id = a.id
    db.close()

    yield applicant_id

    db = SessionLocal()
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


class TestApplicantFieldEncryption:
    def test_columns_are_bytea_not_numeric(self):
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = 'applicants' AND column_name IN "
                    "('stated_income', 'stated_loan_amount', 'stated_property_value', 'stated_dti')"
                )
            ).all()
        types_by_column = {row[0]: row[1] for row in rows}
        assert set(types_by_column) == {
            "stated_income",
            "stated_loan_amount",
            "stated_property_value",
            "stated_dti",
        }
        assert all(t == "bytea" for t in types_by_column.values())

    def test_raw_select_does_not_contain_plaintext_value(self, applicant):
        with engine.connect() as conn:
            raw = conn.execute(
                text("SELECT stated_income FROM applicants WHERE id = :id"),
                {"id": str(applicant)},
            ).scalar_one()
        # The raw bytea ciphertext must not simply be the ASCII digits of
        # the plaintext value.
        assert b"123456.78" not in bytes(raw)

    def test_orm_transparently_decrypts_to_the_original_value(self, applicant):
        db = SessionLocal()
        fetched = db.get(Applicant, applicant)
        assert float(fetched.stated_income) == 123456.78
        assert float(fetched.stated_loan_amount) == 400000.00
        assert float(fetched.stated_property_value) == 450000.00
        assert float(fetched.stated_dti) == 33.25
        db.close()

    def test_wrong_key_cannot_decrypt(self, applicant):
        # A query using the wrong symmetric key must fail rather than
        # silently returning plaintext or garbage that happens to parse.
        with engine.connect() as conn, pytest.raises(Exception):
            conn.execute(
                text(
                    "SELECT pgp_sym_decrypt(stated_income, 'definitely-the-wrong-key') FROM applicants WHERE id = :id"
                ),
                {"id": str(applicant)},
            ).scalar_one()
