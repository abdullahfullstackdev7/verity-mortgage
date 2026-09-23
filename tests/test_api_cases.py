from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.document import Document
from backend.app.db.models.enums import UserRole
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.db.models.user import User
from backend.app.main import app
from backend.app.services import user_service
from conftest import requires_db

pytestmark = requires_db

MINIMAL_PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<< >>\nendobj\ntrailer<< >>\n%%EOF"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_user(role: UserRole) -> dict:
    db = SessionLocal()
    email = f"{role.value}-{uuid.uuid4().hex[:8]}@example.com"
    password = "a reasonably long password"
    user = user_service.create_user(db, email, password, role)
    user_id = user.id
    db.close()
    return {"email": email, "password": password, "id": user_id}


def _cleanup_user(user_id: uuid.UUID) -> None:
    db = SessionLocal()
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


def _token_for(client: TestClient, creds: dict) -> str:
    resp = client.post(
        "/api/v1/auth/login", json={"email": creds["email"], "password": creds["password"]}
    )
    return resp.json()["access_token"]


@pytest.fixture
def loan_officer(client):
    user = _make_user(UserRole.LOAN_OFFICER)
    user["token"] = _token_for(client, user)
    yield user
    _cleanup_user(user["id"])


@pytest.fixture
def underwriter(client):
    user = _make_user(UserRole.UNDERWRITER)
    user["token"] = _token_for(client, user)
    yield user
    _cleanup_user(user["id"])


@pytest.fixture
def applicant():
    db = SessionLocal()
    a = Applicant(
        id=uuid.uuid4(),
        name="Test Applicant",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"api-test:{uuid.uuid4()}",
        stated_income=90000,
        stated_loan_amount=300000,
        stated_property_value=340000,
        stated_dti=32,
    )
    db.add(a)
    db.commit()
    applicant_id = a.id
    db.close()

    yield applicant_id

    db = SessionLocal()
    case_ids = [c.id for c in db.query(Case.id).filter(Case.applicant_id == applicant_id)]
    if case_ids:
        db.query(Document).filter(Document.case_id.in_(case_ids)).delete(
            synchronize_session=False
        )
        db.query(Case).filter(Case.id.in_(case_ids)).delete(synchronize_session=False)
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestCaseCreation:
    def test_loan_officer_can_create_case(self, client, loan_officer, applicant):
        resp = client.post(
            "/api/v1/cases",
            json={"applicant_id": str(applicant)},
            headers=_auth(loan_officer["token"]),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["applicant_id"] == str(applicant)
        assert body["status"] == "submitted"

    def test_underwriter_cannot_create_case(self, client, underwriter, applicant):
        resp = client.post(
            "/api/v1/cases",
            json={"applicant_id": str(applicant)},
            headers=_auth(underwriter["token"]),
        )
        assert resp.status_code == 403

    def test_create_case_for_unknown_applicant_returns_400(self, client, loan_officer):
        resp = client.post(
            "/api/v1/cases",
            json={"applicant_id": str(uuid.uuid4())},
            headers=_auth(loan_officer["token"]),
        )
        assert resp.status_code == 400

    def test_create_case_requires_authentication(self, client, applicant):
        resp = client.post("/api/v1/cases", json={"applicant_id": str(applicant)})
        assert resp.status_code == 401


class TestCaseListingAndDetail:
    def test_list_and_get_case(self, client, loan_officer, applicant):
        create_resp = client.post(
            "/api/v1/cases",
            json={"applicant_id": str(applicant)},
            headers=_auth(loan_officer["token"]),
        )
        case_id = create_resp.json()["id"]

        list_resp = client.get(
            "/api/v1/cases", params={"status": "submitted"}, headers=_auth(loan_officer["token"])
        )
        assert list_resp.status_code == 200
        page = list_resp.json()
        assert any(c["id"] == case_id for c in page["items"])
        assert page["page"] == 1

        detail_resp = client.get(f"/api/v1/cases/{case_id}", headers=_auth(loan_officer["token"]))
        assert detail_resp.status_code == 200
        assert detail_resp.json()["id"] == case_id

    def test_get_unknown_case_returns_404(self, client, loan_officer):
        resp = client.get(f"/api/v1/cases/{uuid.uuid4()}", headers=_auth(loan_officer["token"]))
        assert resp.status_code == 404


class TestCaseStatusUpdate:
    def test_underwriter_can_update_status(self, client, loan_officer, underwriter, applicant):
        create_resp = client.post(
            "/api/v1/cases",
            json={"applicant_id": str(applicant)},
            headers=_auth(loan_officer["token"]),
        )
        case_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "under_review"},
            headers=_auth(underwriter["token"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "under_review"

    def test_loan_officer_cannot_update_status(self, client, loan_officer, applicant):
        create_resp = client.post(
            "/api/v1/cases",
            json={"applicant_id": str(applicant)},
            headers=_auth(loan_officer["token"]),
        )
        case_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "under_review"},
            headers=_auth(loan_officer["token"]),
        )
        assert resp.status_code == 403


class TestDocumentUpload:
    def test_loan_officer_can_upload_pdf(self, client, loan_officer, applicant, tmp_path):
        create_resp = client.post(
            "/api/v1/cases",
            json={"applicant_id": str(applicant)},
            headers=_auth(loan_officer["token"]),
        )
        case_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            data={"doc_type": "paystub"},
            files={"file": ("paystub.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
            headers=_auth(loan_officer["token"]),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["doc_type"] == "paystub"
        assert body["ocr_status"] == "pending_ocr"
        assert Path(body["file_path"]).exists()

        list_resp = client.get(
            f"/api/v1/cases/{case_id}/documents", headers=_auth(loan_officer["token"])
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        shutil.rmtree(Path(settings.document_storage_dir) / case_id, ignore_errors=True)

    def test_non_pdf_content_is_rejected_even_with_pdf_extension(
        self, client, loan_officer, applicant
    ):
        create_resp = client.post(
            "/api/v1/cases",
            json={"applicant_id": str(applicant)},
            headers=_auth(loan_officer["token"]),
        )
        case_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            data={"doc_type": "paystub"},
            files={"file": ("fake.pdf", b"not actually a pdf", "application/pdf")},
            headers=_auth(loan_officer["token"]),
        )
        assert resp.status_code == 415

    def test_underwriter_cannot_upload_documents(self, client, underwriter):
        # Underwriters can't create cases either, so use a case id that need
        # not exist: RBAC should reject the request before the case lookup.
        resp = client.post(
            f"/api/v1/cases/{uuid.uuid4()}/documents",
            data={"doc_type": "paystub"},
            files={"file": ("paystub.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
            headers=_auth(underwriter["token"]),
        )
        assert resp.status_code == 403
