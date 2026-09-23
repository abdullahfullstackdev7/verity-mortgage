from __future__ import annotations

import uuid

import pytest
from conftest import requires_db
from fastapi.testclient import TestClient

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.case_summary import CaseSummary
from backend.app.db.models.enums import UserRole
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.db.models.user import User
from backend.app.main import app
from backend.app.services import user_service
from backend.app.services.llm import provider as llm_provider

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
def case(client, loan_officer):
    db = SessionLocal()
    applicant = Applicant(
        id=uuid.uuid4(),
        name="API Summary Applicant",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"api-summary-test:{uuid.uuid4()}",
        stated_income=100_000,
        stated_loan_amount=300_000,
        stated_property_value=340_000,
        stated_dti=36,
    )
    db.add(applicant)
    db.commit()
    applicant_id = applicant.id
    db.close()

    headers = {"Authorization": f"Bearer {loan_officer['token']}"}
    resp = client.post("/api/v1/cases", json={"applicant_id": str(applicant_id)}, headers=headers)
    case_id = resp.json()["id"]

    yield case_id

    db = SessionLocal()
    db.query(CaseSummary).filter(CaseSummary.case_id == case_id).delete()
    db.query(Case).filter(Case.id == case_id).delete()
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


class TestSummaryEndpoints:
    def test_get_summary_before_generation_is_404(self, client, loan_officer, case):
        headers = {"Authorization": f"Bearer {loan_officer['token']}"}
        resp = client.get(f"/api/v1/cases/{case}/summary", headers=headers)
        assert resp.status_code == 404

    def test_generate_without_provider_returns_502(self, client, loan_officer, case, monkeypatch):
        monkeypatch.setattr(llm_provider, "complete_with_usage_and_failover", lambda prompt: None)
        headers = {"Authorization": f"Bearer {loan_officer['token']}"}
        resp = client.post(f"/api/v1/cases/{case}/summary", headers=headers)
        assert resp.status_code == 502

    def test_generate_then_get_summary(self, client, loan_officer, case, monkeypatch):
        monkeypatch.setattr(
            llm_provider,
            "complete_with_usage_and_failover",
            lambda prompt: (
                '{"narrative": "All checks passed within tolerance.", "recommendation": "approve"}',
                "fake-provider",
                77,
            ),
        )
        headers = {"Authorization": f"Bearer {loan_officer['token']}"}

        gen_resp = client.post(f"/api/v1/cases/{case}/summary", headers=headers)
        assert gen_resp.status_code == 200
        body = gen_resp.json()
        assert body["recommendation"] == "approve"
        assert body["generated_by_model"] == "fake-provider"
        assert body["token_count"] == 77

        get_resp = client.get(f"/api/v1/cases/{case}/summary", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == body["id"]

    def test_generate_requires_authentication(self, client, case):
        client.cookies.clear()
        resp = client.post(f"/api/v1/cases/{case}/summary")
        assert resp.status_code == 401
