"""Seed a fixed, known set of fixture data for the Playwright E2E suite.

Idempotent: deletes any previously seeded "e2e-" data before recreating it,
so repeated CI/local runs don't accumulate rows. Prints a single JSON object
to stdout with the credentials and case id the Playwright tests read.

    uv run python -m scripts.e2e_seed
"""

from __future__ import annotations

import json
import uuid

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.case_summary import CaseSummary
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.document import Document
from backend.app.db.models.enums import (
    CaseStatus,
    DiscrepancySeverity,
    DocumentType,
    OcrStatus,
    Recommendation,
    UserRole,
)
from backend.app.db.models.extracted_field import ExtractedField
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.db.models.user import User
from backend.app.services import user_service
from backend.app.services.summary.service import compute_discrepancy_fingerprint

UNDERWRITER_EMAIL = "e2e-underwriter@e2e-fixtures.example.com"
UNDERWRITER_PASSWORD = "e2e-underwriter-password-123"
APPLICANT_MARKER = "e2e-fixture-applicant"


def _wipe_previous(db) -> None:
    old_applicant = db.query(Applicant).filter(Applicant.hmda_source_id == APPLICANT_MARKER).one_or_none()
    if old_applicant is not None:
        case_ids = [c.id for c in db.query(Case).filter(Case.applicant_id == old_applicant.id).all()]
        for case_id in case_ids:
            db.query(CaseSummary).filter(CaseSummary.case_id == case_id).delete()
            db.query(Discrepancy).filter(Discrepancy.case_id == case_id).delete()
            doc_ids = [d.id for d in db.query(Document).filter(Document.case_id == case_id).all()]
            for doc_id in doc_ids:
                db.query(ExtractedField).filter(ExtractedField.document_id == doc_id).delete()
            db.query(Document).filter(Document.case_id == case_id).delete()
        db.query(Case).filter(Case.applicant_id == old_applicant.id).delete()
        db.delete(old_applicant)

    old_user = db.query(User).filter(User.email == UNDERWRITER_EMAIL).one_or_none()
    if old_user is not None:
        db.query(RefreshToken).filter(RefreshToken.user_id == old_user.id).delete()
        db.delete(old_user)
    db.commit()


def seed() -> dict:
    db = SessionLocal()
    try:
        _wipe_previous(db)

        user_service.create_user(db, UNDERWRITER_EMAIL, UNDERWRITER_PASSWORD, UserRole.UNDERWRITER)

        applicant = Applicant(
            id=uuid.uuid4(),
            name="Jordan E2E Applicant",
            address="482 Fixture Lane, Testville, CA 94000",
            employer_name="Fixture Robotics Inc",
            hmda_source_id=APPLICANT_MARKER,
            stated_income=92_000.0,
            stated_loan_amount=300_000,
            stated_property_value=340_000,
            stated_dti=32,
        )
        db.add(applicant)
        db.flush()

        case = Case(applicant_id=applicant.id, status=CaseStatus.UNDER_REVIEW)
        db.add(case)
        db.flush()

        document = Document(
            case_id=case.id,
            doc_type=DocumentType.PAYSTUB,
            file_path="/fixtures/e2e/paystub.pdf",
            ocr_status=OcrStatus.COMPLETED,
        )
        db.add(document)
        db.flush()

        db.add(
            ExtractedField(
                document_id=document.id,
                field_name="gross_pay_current",
                extracted_value="2692.31",
                confidence_score=0.97,
                raw_text_snippet="Gross Pay: $2,692.31",
            )
        )

        discrepancy = Discrepancy(
            case_id=case.id,
            field_name="income_paystub",
            stated_value="92000.00",
            document_value="70000.06",
            variance_pct=23.9,
            severity=DiscrepancySeverity.MAJOR,
            source_document_id=document.id,
        )
        db.add(discrepancy)
        db.flush()

        summary = CaseSummary(
            case_id=case.id,
            narrative_text=(
                "The applicant's stated income of $92,000 differs materially from the "
                "$70,000.06 annualized income shown on the submitted pay stub, a 23.9% "
                "variance that exceeds the major-discrepancy threshold. All other "
                "verification checks passed."
            ),
            recommendation=Recommendation.REFER,
            generated_by_model="e2e-fixture",
            token_count=None,
            discrepancy_fingerprint=compute_discrepancy_fingerprint([discrepancy]),
        )
        db.add(summary)
        db.commit()

        return {
            "underwriter_email": UNDERWRITER_EMAIL,
            "underwriter_password": UNDERWRITER_PASSWORD,
            "case_id": str(case.id),
            "applicant_name": applicant.name,
        }
    finally:
        db.close()


if __name__ == "__main__":
    print(json.dumps(seed()))
