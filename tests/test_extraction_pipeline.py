from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.document import Document
from backend.app.db.models.document_embedding import DocumentEmbedding
from backend.app.db.models.enums import CaseStatus, DocumentType, OcrStatus
from backend.app.db.models.extracted_field import ExtractedField
from backend.app.services.extraction.pipeline import ExtractionError, extract_document
from conftest import requires_db
from generators.identity import build_identity
from generators.paystub_generator import generate as generate_paystub

pytestmark = requires_db

TEST_APPLICANT_ID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def case_with_paystub(tmp_path):
    db = SessionLocal()

    applicant = Applicant(
        id=uuid.UUID(TEST_APPLICANT_ID),
        name="Test Applicant",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"extraction-test:{uuid.uuid4()}",
        stated_income=92000,
        stated_loan_amount=300000,
        stated_property_value=340000,
        stated_dti=32,
    )
    db.add(applicant)
    db.flush()

    case = Case(applicant_id=applicant.id, status=CaseStatus.SUBMITTED)
    db.add(case)
    db.flush()

    pdf_path = tmp_path / "paystub.pdf"
    identity = build_identity(str(applicant.id))
    generate_paystub(str(applicant.id), 92000.0, identity, pdf_path)

    document = Document(
        case_id=case.id,
        doc_type=DocumentType.PAYSTUB,
        file_path=str(pdf_path),
        ocr_status=OcrStatus.PENDING_OCR,
    )
    db.add(document)
    db.commit()
    document_id = document.id
    case_id = case.id
    applicant_id = applicant.id
    db.close()

    yield document_id

    db = SessionLocal()
    db.query(ExtractedField).filter(ExtractedField.document_id == document_id).delete()
    db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == document_id).delete()
    db.query(Document).filter(Document.id == document_id).delete()
    db.query(Case).filter(Case.id == case_id).delete()
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


class TestExtractDocument:
    def test_extracts_expected_fields_with_reasonable_confidence(self, case_with_paystub):
        db = SessionLocal()
        document = db.get(Document, case_with_paystub)

        fields = extract_document(db, document)

        field_names = {f.field_name for f in fields}
        assert "employer_name" in field_names
        assert "gross_pay_current" in field_names
        for field in fields:
            assert 0.0 <= field.confidence_score <= 1.0

        db.refresh(document)
        assert document.ocr_status == OcrStatus.COMPLETED
        db.close()

    def test_creates_embedding_for_employer_name(self, case_with_paystub):
        db = SessionLocal()
        document = db.get(Document, case_with_paystub)
        extract_document(db, document)

        embeddings = (
            db.query(DocumentEmbedding)
            .filter(DocumentEmbedding.document_id == document.id)
            .all()
        )
        assert any(e.field_name == "employer_name" for e in embeddings)
        assert len(embeddings[0].embedding) == 384
        db.close()

    def test_rerun_without_force_is_a_no_op(self, case_with_paystub):
        db = SessionLocal()
        document = db.get(Document, case_with_paystub)

        first_run = extract_document(db, document)
        first_ids = {f.id for f in first_run}

        second_run = extract_document(db, document)
        second_ids = {f.id for f in second_run}

        assert first_ids == second_ids

        count = (
            db.query(ExtractedField).filter(ExtractedField.document_id == document.id).count()
        )
        assert count == len(first_ids)
        db.close()

    def test_force_rerun_replaces_rows(self, case_with_paystub):
        db = SessionLocal()
        document = db.get(Document, case_with_paystub)

        first_run = extract_document(db, document)
        first_ids = {f.id for f in first_run}

        second_run = extract_document(db, document, force=True)
        second_ids = {f.id for f in second_run}

        # Rows were actually replaced (new primary keys), not just returned again.
        assert first_ids.isdisjoint(second_ids)

        count = (
            db.query(ExtractedField).filter(ExtractedField.document_id == document.id).count()
        )
        assert count == len(second_ids)
        db.close()

    def test_ocr_failure_marks_document_failed_and_raises(self, case_with_paystub):
        db = SessionLocal()
        document = db.get(Document, case_with_paystub)
        document.file_path = str(Path(document.file_path).parent / "does_not_exist.pdf")
        db.commit()

        with pytest.raises(ExtractionError):
            extract_document(db, document)

        db.refresh(document)
        assert document.ocr_status == OcrStatus.FAILED
        db.close()
