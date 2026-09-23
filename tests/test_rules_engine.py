from __future__ import annotations

import uuid

import pytest
from conftest import requires_db

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.document import Document
from backend.app.db.models.document_embedding import DocumentEmbedding
from backend.app.db.models.enums import CaseStatus, DocumentType, OcrStatus
from backend.app.db.models.extracted_field import ExtractedField
from backend.app.services.extraction.embedding import embed_text
from backend.app.services.rules.engine import run_verification

pytestmark = requires_db

STATED_INCOME = 100_000.0
STATED_DTI = 36.0
EMPLOYER_NAME = "Acme Corp"
# Mirrors engine.check_bank_deposit's expected-deposit formula exactly
# (combined tax rate 0.2365, nominal 30-day statement period).
EXPECTED_STATEMENT_DEPOSIT = STATED_INCOME * (1 - 0.2365) * (30 / 365)


def _add_document_with_fields(
    db, case_id, doc_type: DocumentType, fields: dict[str, str], embeddings: dict[str, str]
) -> Document:
    document = Document(
        case_id=case_id,
        doc_type=doc_type,
        file_path=f"/fake/{doc_type.value}.pdf",
        ocr_status=OcrStatus.COMPLETED,
    )
    db.add(document)
    db.flush()

    for field_name, value in fields.items():
        db.add(
            ExtractedField(
                document_id=document.id,
                field_name=field_name,
                extracted_value=value,
                confidence_score=0.9,
                raw_text_snippet=value,
            )
        )
    for field_name, text_value in embeddings.items():
        db.add(
            DocumentEmbedding(
                document_id=document.id,
                field_name=field_name,
                value_text=text_value,
                embedding=embed_text(text_value),
            )
        )
    db.flush()
    return document


@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.rollback()
    db.close()


@pytest.fixture
def applicant_and_case(db_session):
    applicant = Applicant(
        id=uuid.uuid4(),
        name="Test Applicant",
        address="1 Test Way",
        employer_name=EMPLOYER_NAME,
        hmda_source_id=f"rules-test:{uuid.uuid4()}",
        stated_income=STATED_INCOME,
        stated_loan_amount=300000,
        stated_property_value=340000,
        stated_dti=STATED_DTI,
    )
    db_session.add(applicant)
    db_session.flush()

    case = Case(applicant_id=applicant.id, status=CaseStatus.SUBMITTED)
    db_session.add(case)
    db_session.commit()

    applicant_id = applicant.id
    case_id = case.id

    yield applicant, case

    db = SessionLocal()
    document_ids = [d.id for d in db.query(Document.id).filter(Document.case_id == case_id)]
    # discrepancies reference documents via source_document_id, so they must
    # go first, before the documents they point at can be deleted.
    db.query(Discrepancy).filter(Discrepancy.case_id == case_id).delete()
    if document_ids:
        db.query(ExtractedField).filter(ExtractedField.document_id.in_(document_ids)).delete(synchronize_session=False)
        db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id.in_(document_ids)).delete(
            synchronize_session=False
        )
        db.query(Document).filter(Document.id.in_(document_ids)).delete(synchronize_session=False)
    db.query(Case).filter(Case.id == case_id).delete()
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


class TestRunVerificationCleanCase:
    def test_matching_documents_produce_no_discrepancies(self, db_session, applicant_and_case):
        _applicant, case = applicant_and_case
        biweekly_gross = str(round(STATED_INCOME / 26, 2))

        _add_document_with_fields(
            db_session,
            case.id,
            DocumentType.PAYSTUB,
            {"gross_pay_current": biweekly_gross, "pay_frequency": "Biweekly", "employer_name": EMPLOYER_NAME},
            {"employer_name": EMPLOYER_NAME},
        )
        _add_document_with_fields(
            db_session,
            case.id,
            DocumentType.W2,
            {"box1_wages": str(STATED_INCOME), "employer_name": EMPLOYER_NAME, "employer_ein": "12-3456789"},
            {"employer_name": EMPLOYER_NAME},
        )
        _add_document_with_fields(
            db_session,
            case.id,
            DocumentType.BANK_STATEMENT,
            {"payroll_deposit_total": str(round(EXPECTED_STATEMENT_DEPOSIT, 2))},
            {},
        )
        db_session.commit()

        discrepancies = run_verification(db_session, case)
        assert discrepancies == []


class TestRunVerificationMismatches:
    def test_income_15_percent_below_stated_flags_income_paystub(self, db_session, applicant_and_case):
        _applicant, case = applicant_and_case
        low_annual = STATED_INCOME * 0.85
        biweekly_gross = str(round(low_annual / 26, 2))

        _add_document_with_fields(
            db_session,
            case.id,
            DocumentType.PAYSTUB,
            {"gross_pay_current": biweekly_gross, "pay_frequency": "Biweekly", "employer_name": EMPLOYER_NAME},
            {"employer_name": EMPLOYER_NAME},
        )
        db_session.commit()

        discrepancies = run_verification(db_session, case)
        by_field = {d.field_name: d for d in discrepancies}
        assert "income_paystub" in by_field
        assert by_field["income_paystub"].severity.value == "minor"

    def test_income_40_percent_below_stated_is_major(self, db_session, applicant_and_case):
        _applicant, case = applicant_and_case
        low_annual = STATED_INCOME * 0.60
        biweekly_gross = str(round(low_annual / 26, 2))

        _add_document_with_fields(
            db_session,
            case.id,
            DocumentType.PAYSTUB,
            {"gross_pay_current": biweekly_gross, "pay_frequency": "Biweekly"},
            {},
        )
        db_session.commit()

        discrepancies = run_verification(db_session, case)
        by_field = {d.field_name: d for d in discrepancies}
        assert by_field["income_paystub"].severity.value == "major"

    def test_mismatched_employer_name_is_flagged(self, db_session, applicant_and_case):
        _applicant, case = applicant_and_case
        _add_document_with_fields(
            db_session,
            case.id,
            DocumentType.W2,
            {"box1_wages": str(STATED_INCOME), "employer_name": "Totally Unrelated Company"},
            {"employer_name": "Totally Unrelated Company"},
        )
        db_session.commit()

        discrepancies = run_verification(db_session, case)
        by_field = {d.field_name: d for d in discrepancies}
        assert "employer_name_w2" in by_field
        assert by_field["employer_name_w2"].document_value == "Totally Unrelated Company"

    def test_source_document_id_is_recorded(self, db_session, applicant_and_case):
        _applicant, case = applicant_and_case
        low_annual = STATED_INCOME * 0.60
        document = _add_document_with_fields(
            db_session,
            case.id,
            DocumentType.PAYSTUB,
            {"gross_pay_current": str(round(low_annual / 26, 2)), "pay_frequency": "Biweekly"},
            {},
        )
        db_session.commit()

        discrepancies = run_verification(db_session, case)
        by_field = {d.field_name: d for d in discrepancies}
        assert by_field["income_paystub"].source_document_id == document.id


class TestRunVerificationIdempotency:
    def test_rerun_without_force_returns_same_rows(self, db_session, applicant_and_case):
        _applicant, case = applicant_and_case
        low_annual = STATED_INCOME * 0.60
        _add_document_with_fields(
            db_session,
            case.id,
            DocumentType.PAYSTUB,
            {"gross_pay_current": str(round(low_annual / 26, 2)), "pay_frequency": "Biweekly"},
            {},
        )
        db_session.commit()

        first = run_verification(db_session, case)
        second = run_verification(db_session, case)
        assert {d.id for d in first} == {d.id for d in second}

    def test_force_rerun_replaces_rows(self, db_session, applicant_and_case):
        _applicant, case = applicant_and_case
        low_annual = STATED_INCOME * 0.60
        _add_document_with_fields(
            db_session,
            case.id,
            DocumentType.PAYSTUB,
            {"gross_pay_current": str(round(low_annual / 26, 2)), "pay_frequency": "Biweekly"},
            {},
        )
        db_session.commit()

        first = run_verification(db_session, case)
        second = run_verification(db_session, case, force=True)
        assert {d.id for d in first}.isdisjoint({d.id for d in second})
