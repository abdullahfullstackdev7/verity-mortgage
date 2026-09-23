from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.document import Document
from backend.app.db.models.document_embedding import DocumentEmbedding
from backend.app.db.models.enums import UserRole
from backend.app.db.models.extracted_field import ExtractedField
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.db.models.user import User
from backend.app.main import app
from backend.app.services import user_service
from conftest import requires_db
from generators.identity import build_identity
from generators.paystub_generator import generate as generate_paystub

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
def case_with_uploaded_paystub(client, loan_officer, tmp_path):
    db = SessionLocal()
    applicant = Applicant(
        id=uuid.uuid4(),
        name="API Test Applicant",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"api-extraction-test:{uuid.uuid4()}",
        stated_income=92000,
        stated_loan_amount=300000,
        stated_property_value=340000,
        stated_dti=32,
    )
    db.add(applicant)
    db.commit()
    applicant_id = applicant.id
    db.close()

    identity = build_identity(str(applicant_id))
    pdf_path = tmp_path / "paystub.pdf"
    generate_paystub(str(applicant_id), 92000.0, identity, pdf_path)

    headers = {"Authorization": f"Bearer {loan_officer['token']}"}
    case_resp = client.post(
        "/api/v1/cases", json={"applicant_id": str(applicant_id)}, headers=headers
    )
    case_id = case_resp.json()["id"]

    with open(pdf_path, "rb") as f:
        upload_resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            data={"doc_type": "paystub"},
            files={"file": ("paystub.pdf", f.read(), "application/pdf")},
            headers=headers,
        )
    document_id = upload_resp.json()["id"]

    yield {"case_id": case_id, "document_id": document_id}

    db = SessionLocal()
    db.query(ExtractedField).filter(ExtractedField.document_id == document_id).delete()
    db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == document_id).delete()
    db.query(Document).filter(Document.id == document_id).delete()
    db.query(Case).filter(Case.id == case_id).delete()
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


class TestExtractionEndpoint:
    def test_extract_then_list_fields(self, client, loan_officer, case_with_uploaded_paystub):
        headers = {"Authorization": f"Bearer {loan_officer['token']}"}
        case_id = case_with_uploaded_paystub["case_id"]
        document_id = case_with_uploaded_paystub["document_id"]

        extract_resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/extract", headers=headers
        )
        assert extract_resp.status_code == 200
        fields = extract_resp.json()
        field_names = {f["field_name"] for f in fields}
        assert "employer_name" in field_names
        assert "gross_pay_current" in field_names

        list_resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}/fields", headers=headers
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == len(fields)

    def test_extract_requires_authentication(self, client, case_with_uploaded_paystub):
        case_id = case_with_uploaded_paystub["case_id"]
        document_id = case_with_uploaded_paystub["document_id"]
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/extract")
        assert resp.status_code == 401

    def test_extract_unknown_document_returns_404(self, client, loan_officer, case_with_uploaded_paystub):
        headers = {"Authorization": f"Bearer {loan_officer['token']}"}
        case_id = case_with_uploaded_paystub["case_id"]
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{uuid.uuid4()}/extract", headers=headers
        )
        assert resp.status_code == 404


class TestDocumentFileDownload:
    def test_downloads_the_uploaded_pdf(self, client, loan_officer, case_with_uploaded_paystub):
        headers = {"Authorization": f"Bearer {loan_officer['token']}"}
        case_id = case_with_uploaded_paystub["case_id"]
        document_id = case_with_uploaded_paystub["document_id"]

        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}/file", headers=headers
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF")

    def test_requires_authentication(self, client, case_with_uploaded_paystub):
        case_id = case_with_uploaded_paystub["case_id"]
        document_id = case_with_uploaded_paystub["document_id"]
        resp = client.get(f"/api/v1/cases/{case_id}/documents/{document_id}/file")
        assert resp.status_code == 401

    def test_unknown_document_returns_404(self, client, loan_officer, case_with_uploaded_paystub):
        headers = {"Authorization": f"Bearer {loan_officer['token']}"}
        case_id = case_with_uploaded_paystub["case_id"]
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{uuid.uuid4()}/file", headers=headers
        )
        assert resp.status_code == 404
