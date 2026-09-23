from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.discrepancy import Discrepancy
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
def case_with_extracted_paystub(client, loan_officer, tmp_path):
    """A case with one paystub document that's already been extracted, with
    a gross pay figure ~40% below stated income so verification finds a
    major discrepancy."""
    db = SessionLocal()
    applicant = Applicant(
        id=uuid.uuid4(),
        name="API Verify Applicant",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"api-verify-test:{uuid.uuid4()}",
        stated_income=100_000,
        stated_loan_amount=300000,
        stated_property_value=340000,
        stated_dti=36,
    )
    db.add(applicant)
    db.commit()
    applicant_id = applicant.id
    db.close()

    identity = build_identity(str(applicant_id))
    pdf_path = tmp_path / "paystub.pdf"
    generate_paystub(str(applicant_id), 60_000.0, identity, pdf_path)  # 40% below stated

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

    client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/extract", headers=headers)

    yield {"case_id": case_id, "document_id": document_id}

    db = SessionLocal()
    db.query(Discrepancy).filter(Discrepancy.case_id == case_id).delete()
    db.query(ExtractedField).filter(ExtractedField.document_id == document_id).delete()
    db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == document_id).delete()
    db.query(Document).filter(Document.id == document_id).delete()
    db.query(Case).filter(Case.id == case_id).delete()
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


class TestVerifyEndpoint:
    def test_verify_then_list_discrepancies(self, client, loan_officer, case_with_extracted_paystub):
        headers = {"Authorization": f"Bearer {loan_officer['token']}"}
        case_id = case_with_extracted_paystub["case_id"]

        verify_resp = client.post(f"/api/v1/cases/{case_id}/verify", headers=headers)
        assert verify_resp.status_code == 200
        discrepancies = verify_resp.json()
        by_field = {d["field_name"]: d for d in discrepancies}
        assert "income_paystub" in by_field
        assert by_field["income_paystub"]["severity"] == "major"

        list_resp = client.get(f"/api/v1/cases/{case_id}/discrepancies", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == len(discrepancies)

    def test_verify_requires_authentication(self, client, case_with_extracted_paystub):
        case_id = case_with_extracted_paystub["case_id"]
        resp = client.post(f"/api/v1/cases/{case_id}/verify")
        assert resp.status_code == 401

    def test_verify_unknown_case_returns_404(self, client, loan_officer):
        headers = {"Authorization": f"Bearer {loan_officer['token']}"}
        resp = client.post(f"/api/v1/cases/{uuid.uuid4()}/verify", headers=headers)
        assert resp.status_code == 404
