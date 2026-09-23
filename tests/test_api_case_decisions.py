from __future__ import annotations

import uuid

import pytest
from conftest import requires_db
from fastapi.testclient import TestClient

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.audit_log import AuditLog
from backend.app.db.models.case import Case
from backend.app.db.models.case_summary import CaseSummary
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.document import Document
from backend.app.db.models.enums import DocumentType, OcrStatus, UserRole
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.db.models.user import User
from backend.app.main import app
from backend.app.services import user_service

pytestmark = requires_db


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_user_and_login(client, role: UserRole):
    db = SessionLocal()
    email = f"{role.value}-{uuid.uuid4().hex[:8]}@example.com"
    password = "a reasonably long password"
    user = user_service.create_user(db, email, password, role)
    user_id = user.id
    db.close()

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"id": user_id, "token": token}


@pytest.fixture
def loan_officer(client):
    user = _make_user_and_login(client, UserRole.LOAN_OFFICER)
    yield user
    db = SessionLocal()
    db.query(RefreshToken).filter(RefreshToken.user_id == user["id"]).delete()
    db.query(User).filter(User.id == user["id"]).delete()
    db.commit()
    db.close()


@pytest.fixture
def underwriter(client):
    user = _make_user_and_login(client, UserRole.UNDERWRITER)
    yield user
    db = SessionLocal()
    db.query(RefreshToken).filter(RefreshToken.user_id == user["id"]).delete()
    db.query(User).filter(User.id == user["id"]).delete()
    db.commit()
    db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def case_id(client, loan_officer):
    db = SessionLocal()
    applicant = Applicant(
        id=uuid.uuid4(),
        name="Decision API Test",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"api-decision-test:{uuid.uuid4()}",
        stated_income=90000,
        stated_loan_amount=300000,
        stated_property_value=340000,
        stated_dti=32,
    )
    db.add(applicant)
    db.commit()
    applicant_id = applicant.id
    db.close()

    resp = client.post(
        "/api/v1/cases",
        json={"applicant_id": str(applicant_id)},
        headers=_auth(loan_officer["token"]),
    )
    cid = resp.json()["id"]

    yield cid

    db = SessionLocal()
    db.query(AuditLog).filter(AuditLog.case_id == cid).delete()
    db.query(CaseSummary).filter(CaseSummary.case_id == cid).delete()
    db.query(Discrepancy).filter(Discrepancy.case_id == cid).delete()
    db.query(Document).filter(Document.case_id == cid).delete()
    db.query(Case).filter(Case.id == cid).delete()
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


def _mark_documents_extracted(case_id: str):
    db = SessionLocal()
    for doc_type in (DocumentType.PAYSTUB, DocumentType.BANK_STATEMENT, DocumentType.W2):
        db.add(
            Document(
                case_id=uuid.UUID(case_id),
                doc_type=doc_type,
                file_path=f"/fake/{doc_type.value}.pdf",
                ocr_status=OcrStatus.COMPLETED,
            )
        )
    db.commit()
    db.close()


class TestSubmitForReview:
    def test_blocked_without_required_documents(self, client, loan_officer, case_id):
        resp = client.post(f"/api/v1/cases/{case_id}/submit-for-review", headers=_auth(loan_officer["token"]))
        assert resp.status_code == 400

    def test_succeeds_once_documents_present(self, client, loan_officer, case_id):
        _mark_documents_extracted(case_id)
        resp = client.post(f"/api/v1/cases/{case_id}/submit-for-review", headers=_auth(loan_officer["token"]))
        assert resp.status_code == 200
        assert resp.json()["status"] == "under_review"

    def test_underwriter_cannot_submit_for_review(self, client, underwriter, case_id):
        _mark_documents_extracted(case_id)
        resp = client.post(f"/api/v1/cases/{case_id}/submit-for-review", headers=_auth(underwriter["token"]))
        assert resp.status_code == 403


class TestAutoRoute:
    def test_clean_case_auto_approves(self, client, loan_officer, case_id):
        _mark_documents_extracted(case_id)
        client.post(f"/api/v1/cases/{case_id}/submit-for-review", headers=_auth(loan_officer["token"]))

        resp = client.post(f"/api/v1/cases/{case_id}/route", headers=_auth(loan_officer["token"]))
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_route_before_review_is_conflict(self, client, loan_officer, case_id):
        resp = client.post(f"/api/v1/cases/{case_id}/route", headers=_auth(loan_officer["token"]))
        assert resp.status_code == 409


class TestDecisionEndpoint:
    def test_underwriter_can_decide_with_override_reason(self, client, loan_officer, underwriter, case_id):
        _mark_documents_extracted(case_id)
        client.post(f"/api/v1/cases/{case_id}/submit-for-review", headers=_auth(loan_officer["token"]))

        resp = client.post(
            f"/api/v1/cases/{case_id}/decision",
            json={"decision": "denied", "override_reason": "Applicant withdrew consent for verification."},
            headers=_auth(underwriter["token"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "denied"

    def test_decision_without_override_reason_and_no_summary_is_400(self, client, loan_officer, underwriter, case_id):
        _mark_documents_extracted(case_id)
        client.post(f"/api/v1/cases/{case_id}/submit-for-review", headers=_auth(loan_officer["token"]))

        resp = client.post(
            f"/api/v1/cases/{case_id}/decision",
            json={"decision": "approved"},
            headers=_auth(underwriter["token"]),
        )
        assert resp.status_code == 400

    def test_loan_officer_cannot_decide(self, client, loan_officer, case_id):
        _mark_documents_extracted(case_id)
        client.post(f"/api/v1/cases/{case_id}/submit-for-review", headers=_auth(loan_officer["token"]))

        resp = client.post(
            f"/api/v1/cases/{case_id}/decision",
            json={"decision": "approved", "override_reason": "n/a"},
            headers=_auth(loan_officer["token"]),
        )
        assert resp.status_code == 403


class TestAuditLogEndpoint:
    def test_audit_log_records_every_transition(self, client, loan_officer, underwriter, case_id):
        _mark_documents_extracted(case_id)
        client.post(f"/api/v1/cases/{case_id}/submit-for-review", headers=_auth(loan_officer["token"]))
        client.post(
            f"/api/v1/cases/{case_id}/decision",
            json={"decision": "approved", "override_reason": "Manually reviewed, all clear."},
            headers=_auth(underwriter["token"]),
        )

        resp = client.get(f"/api/v1/cases/{case_id}/audit-log", headers=_auth(loan_officer["token"]))
        assert resp.status_code == 200
        actions = [e["action"] for e in resp.json()]
        assert actions == [
            "status_changed_to_documents_pending",
            "status_changed_to_under_review",
            "status_changed_to_approved",
        ]
