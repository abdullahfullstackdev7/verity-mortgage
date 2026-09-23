from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.enums import CaseStatus, DiscrepancySeverity, UserRole
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.db.models.user import User
from backend.app.main import app
from backend.app.services import user_service
from conftest import requires_db

pytestmark = requires_db


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def loan_officer(client):
    db = SessionLocal()
    email = f"officer-{uuid.uuid4().hex[:8]}@example.com"
    password = "a reasonably long password"
    user = user_service.create_user(db, email, password, UserRole.LOAN_OFFICER)
    user_id = user.id
    db.close()

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]

    yield {"id": user_id, "token": token}

    db = SessionLocal()
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


@pytest.fixture
def case_with_discrepancies(loan_officer):
    db = SessionLocal()
    applicant = Applicant(
        id=uuid.uuid4(),
        name="Denormalized Test Applicant",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"case-list-test:{uuid.uuid4()}",
        stated_income=100000,
        stated_loan_amount=275000,
        stated_property_value=310000,
        stated_dti=30,
    )
    db.add(applicant)
    db.flush()
    case = Case(applicant_id=applicant.id, status=CaseStatus.UNDER_REVIEW)
    db.add(case)
    db.flush()
    db.add(
        Discrepancy(
            case_id=case.id,
            field_name="income_paystub",
            stated_value="100000.00",
            document_value="60000.00",
            variance_pct=40.0,
            severity=DiscrepancySeverity.MAJOR,
            source_document_id=None,
        )
    )
    db.add(
        Discrepancy(
            case_id=case.id,
            field_name="employer_name_w2",
            stated_value="Acme",
            document_value="Acme Co",
            variance_pct=12.0,
            severity=DiscrepancySeverity.MINOR,
            source_document_id=None,
        )
    )
    db.commit()
    applicant_id, case_id = applicant.id, case.id
    db.close()

    yield case_id

    db = SessionLocal()
    db.query(Discrepancy).filter(Discrepancy.case_id == case_id).delete()
    db.query(Case).filter(Case.id == case_id).delete()
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


class TestEnrichedCaseList:
    def test_list_includes_applicant_and_discrepancy_counts(
        self, client, loan_officer, case_with_discrepancies
    ):
        resp = client.get(
            "/api/v1/cases",
            params={"status": "under_review"},
            headers={"Authorization": f"Bearer {loan_officer['token']}"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        row = next(i for i in items if i["id"] == str(case_with_discrepancies))

        assert row["applicant_name"] == "Denormalized Test Applicant"
        assert row["stated_loan_amount"] == 275000.0
        assert row["discrepancy_count"] == 2
        assert row["major_discrepancy_count"] == 1
        assert row["assigned_underwriter_email"] is None
