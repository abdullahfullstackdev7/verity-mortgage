"""End-to-end check that the rules engine's verdict on a real generated pay
stub matches the ground truth recorded by Phase 2's discrepancy injector:
an applicant Phase 2 marked as discrepant should come out flagged (with
severity matching the injected variance band), and a clean applicant should
come out clean. This exercises the full OCR -> parse -> verify chain, not
just the pure rule functions.
"""

from __future__ import annotations

import uuid

from conftest import requires_db

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.document import Document
from backend.app.db.models.document_embedding import DocumentEmbedding
from backend.app.db.models.enums import CaseStatus, DocumentType, OcrStatus
from backend.app.db.models.extracted_field import ExtractedField
from backend.app.services.extraction.pipeline import extract_document
from backend.app.services.rules.engine import run_verification
from generators import discrepancy
from generators.identity import build_identity
from generators.paystub_generator import generate as generate_paystub

pytestmark = requires_db

STATED_INCOME = 92_000.0


def _find_applicant_id(want_injected: bool, search_space: int = 500) -> str:
    for i in range(search_space):
        candidate = f"ground-truth-search-{i}"
        if discrepancy.decide(candidate).injected == want_injected:
            return candidate
    raise AssertionError(f"couldn't find an applicant_id with injected={want_injected}")


def _build_case_with_paystub(tmp_path, applicant_id_str: str):
    db = SessionLocal()
    applicant = Applicant(
        id=uuid.uuid5(uuid.NAMESPACE_URL, applicant_id_str),
        name="Ground Truth Test",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"ground-truth-test:{applicant_id_str}",
        stated_income=STATED_INCOME,
        stated_loan_amount=300000,
        stated_property_value=340000,
        stated_dti=32,
    )
    db.add(applicant)
    db.flush()

    case = Case(applicant_id=applicant.id, status=CaseStatus.SUBMITTED)
    db.add(case)
    db.flush()

    # The discrepancy injector's decision (and the paystub figure it
    # produces) is keyed on `applicant_id_str`, matching how build_all.py
    # drives generation in Phase 2 - not the DB row's UUID, which is
    # derived from it just for a stable primary key here.
    identity = build_identity(applicant_id_str)
    pdf_path = tmp_path / "paystub.pdf"
    _document_income, decision = generate_paystub(applicant_id_str, STATED_INCOME, identity, pdf_path)

    document = Document(
        case_id=case.id,
        doc_type=DocumentType.PAYSTUB,
        file_path=str(pdf_path),
        ocr_status=OcrStatus.PENDING_OCR,
    )
    db.add(document)
    db.commit()

    ids = {"applicant_id": applicant.id, "case_id": case.id, "document_id": document.id}
    db.close()
    return ids, decision


def _cleanup(ids: dict):
    db = SessionLocal()
    db.query(Discrepancy).filter(Discrepancy.case_id == ids["case_id"]).delete()
    db.query(ExtractedField).filter(ExtractedField.document_id == ids["document_id"]).delete()
    db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == ids["document_id"]).delete()
    db.query(Document).filter(Document.id == ids["document_id"]).delete()
    db.query(Case).filter(Case.id == ids["case_id"]).delete()
    db.query(Applicant).filter(Applicant.id == ids["applicant_id"]).delete()
    db.commit()
    db.close()


class TestMatchesPhase2GroundTruth:
    def test_applicant_with_injected_discrepancy_is_flagged_with_matching_severity(self, tmp_path):
        applicant_id_str = _find_applicant_id(want_injected=True)
        ids, decision = _build_case_with_paystub(tmp_path, applicant_id_str)
        assert decision.injected  # sanity-check the ground truth itself

        db = SessionLocal()
        document = db.get(Document, ids["document_id"])
        extract_document(db, document)
        case = db.get(Case, ids["case_id"])
        discrepancies = run_verification(db, case)
        db.close()

        by_field = {d.field_name: d for d in discrepancies}
        assert "income_paystub" in by_field, (
            f"Phase 2 injected a {decision.variance_pct:.1f}% {decision.direction} "
            "discrepancy but the rules engine found none"
        )

        expected_severity = "minor" if decision.variance_pct <= 20.0 else "major"
        assert by_field["income_paystub"].severity.value == expected_severity

        _cleanup(ids)

    def test_clean_applicant_is_not_flagged_for_income(self, tmp_path):
        applicant_id_str = _find_applicant_id(want_injected=False)
        ids, decision = _build_case_with_paystub(tmp_path, applicant_id_str)
        assert not decision.injected  # sanity-check the ground truth itself

        db = SessionLocal()
        document = db.get(Document, ids["document_id"])
        extract_document(db, document)
        case = db.get(Case, ids["case_id"])
        discrepancies = run_verification(db, case)
        db.close()

        by_field = {d.field_name: d for d in discrepancies}
        assert "income_paystub" not in by_field

        _cleanup(ids)
