from __future__ import annotations

import uuid

import pytest
from conftest import requires_db
from fastapi.testclient import TestClient

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.enums import UserRole
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.db.models.user import User
from backend.app.main import app
from backend.app.services import user_service

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
def applicants():
    db = SessionLocal()
    made = []
    for name in ("Alpha Applicant", "Beta Borrower"):
        a = Applicant(
            id=uuid.uuid4(),
            name=name,
            address="1 Test Way",
            employer_name="Test Employer",
            hmda_source_id=f"applicant-api-test:{uuid.uuid4()}",
            stated_income=90000,
            stated_loan_amount=300000,
            stated_property_value=340000,
            stated_dti=32,
        )
        db.add(a)
        made.append(a)
    db.commit()
    ids = [a.id for a in made]
    db.close()

    yield ids

    db = SessionLocal()
    db.query(Applicant).filter(Applicant.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestListApplicants:
    def test_requires_authentication(self, client):
        resp = client.get("/api/v1/applicants")
        assert resp.status_code == 401

    def test_lists_applicants(self, client, loan_officer, applicants):
        resp = client.get("/api/v1/applicants", headers=_auth(loan_officer["token"]))
        assert resp.status_code == 200
        body = resp.json()
        names = {item["name"] for item in body["items"]}
        assert {"Alpha Applicant", "Beta Borrower"} <= names

    def test_search_filters_by_name(self, client, loan_officer, applicants):
        resp = client.get("/api/v1/applicants", params={"search": "Alpha"}, headers=_auth(loan_officer["token"]))
        assert resp.status_code == 200
        names = {item["name"] for item in resp.json()["items"]}
        assert "Alpha Applicant" in names
        assert "Beta Borrower" not in names


class TestGetApplicant:
    def test_returns_applicant(self, client, loan_officer, applicants):
        applicant_id = applicants[0]
        resp = client.get(f"/api/v1/applicants/{applicant_id}", headers=_auth(loan_officer["token"]))
        assert resp.status_code == 200
        assert resp.json()["id"] == str(applicant_id)

    def test_unknown_applicant_returns_404(self, client, loan_officer):
        resp = client.get(f"/api/v1/applicants/{uuid.uuid4()}", headers=_auth(loan_officer["token"]))
        assert resp.status_code == 404
