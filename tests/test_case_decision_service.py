from __future__ import annotations

import uuid

import pytest

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.audit_log import AuditLog
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
)
from backend.app.services.case_decision_service import (
    DecisionError,
    auto_route_case,
    record_underwriter_decision,
    submit_for_review,
)
from backend.app.services.case_state_machine import (
    GuardNotSatisfiedError,
    TransitionNotAllowedError,
)
from conftest import requires_db

pytestmark = requires_db


@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.rollback()
    db.close()


@pytest.fixture
def case(db_session):
    applicant = Applicant(
        id=uuid.uuid4(),
        name="Decision Test",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"decision-test:{uuid.uuid4()}",
        stated_income=90000,
        stated_loan_amount=300000,
        stated_property_value=340000,
        stated_dti=32,
    )
    db_session.add(applicant)
    db_session.flush()
    case = Case(applicant_id=applicant.id, status=CaseStatus.SUBMITTED)
    db_session.add(case)
    db_session.commit()

    applicant_id, case_id = applicant.id, case.id
    yield case

    db = SessionLocal()
    db.query(AuditLog).filter(AuditLog.case_id == case_id).delete()
    db.query(CaseSummary).filter(CaseSummary.case_id == case_id).delete()
    db.query(Discrepancy).filter(Discrepancy.case_id == case_id).delete()
    db.query(Document).filter(Document.case_id == case_id).delete()
    db.query(Case).filter(Case.id == case_id).delete()
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


def _add_documents(db, case, ocr_status: OcrStatus):
    for doc_type in (DocumentType.PAYSTUB, DocumentType.BANK_STATEMENT, DocumentType.W2):
        db.add(
            Document(
                case_id=case.id,
                doc_type=doc_type,
                file_path=f"/fake/{doc_type.value}.pdf",
                ocr_status=ocr_status,
            )
        )
    db.commit()


class TestSubmitForReview:
    def test_blocked_when_documents_missing(self, db_session, case):
        with pytest.raises(GuardNotSatisfiedError):
            submit_for_review(db_session, case, actor="officer@example.com")
        assert case.status == CaseStatus.SUBMITTED

    def test_succeeds_and_passes_through_documents_pending(self, db_session, case):
        _add_documents(db_session, case, OcrStatus.PENDING_OCR)

        result = submit_for_review(db_session, case, actor="officer@example.com")
        assert result.status == CaseStatus.UNDER_REVIEW

        entries = (
            db_session.query(AuditLog)
            .filter(AuditLog.case_id == case.id)
            .order_by(AuditLog.created_at)
            .all()
        )
        actions = [e.action for e in entries]
        assert actions == ["status_changed_to_documents_pending", "status_changed_to_under_review"]

    def test_wrong_starting_status_is_rejected(self, db_session, case):
        _add_documents(db_session, case, OcrStatus.PENDING_OCR)
        submit_for_review(db_session, case, actor="officer@example.com")  # -> under_review

        with pytest.raises(TransitionNotAllowedError):
            submit_for_review(db_session, case, actor="officer@example.com")


class TestAutoRouteCase:
    def test_requires_under_review_status(self, db_session, case):
        with pytest.raises(TransitionNotAllowedError):
            auto_route_case(db_session, case)

    def test_blocked_when_documents_not_extracted(self, db_session, case):
        _add_documents(db_session, case, OcrStatus.PENDING_OCR)
        submit_for_review(db_session, case, actor="officer@example.com")

        with pytest.raises(GuardNotSatisfiedError):
            auto_route_case(db_session, case)

    def test_no_discrepancies_auto_approves(self, db_session, case):
        _add_documents(db_session, case, OcrStatus.COMPLETED)
        submit_for_review(db_session, case, actor="officer@example.com")

        result = auto_route_case(db_session, case)
        assert result.status == CaseStatus.APPROVED

    def test_minor_only_discrepancies_auto_refer(self, db_session, case):
        _add_documents(db_session, case, OcrStatus.COMPLETED)
        submit_for_review(db_session, case, actor="officer@example.com")
        db_session.add(
            Discrepancy(
                case_id=case.id,
                field_name="income_paystub",
                stated_value="90000.00",
                document_value="80000.00",
                variance_pct=11.1,
                severity=DiscrepancySeverity.MINOR,
                source_document_id=None,
            )
        )
        db_session.commit()

        result = auto_route_case(db_session, case)
        assert result.status == CaseStatus.REFERRED

    def test_major_discrepancy_blocks_auto_approval_and_stays_under_review(self, db_session, case):
        _add_documents(db_session, case, OcrStatus.COMPLETED)
        submit_for_review(db_session, case, actor="officer@example.com")
        db_session.add(
            Discrepancy(
                case_id=case.id,
                field_name="income_paystub",
                stated_value="90000.00",
                document_value="50000.00",
                variance_pct=44.0,
                severity=DiscrepancySeverity.MAJOR,
                source_document_id=None,
            )
        )
        db_session.commit()

        result = auto_route_case(db_session, case)
        assert result.status == CaseStatus.UNDER_REVIEW  # unchanged, blocked

        blocked_entries = [
            e
            for e in db_session.query(AuditLog).filter(AuditLog.case_id == case.id)
            if e.action == "auto_route_blocked"
        ]
        assert len(blocked_entries) == 1
        assert "income_paystub" in blocked_entries[0].rule_or_evidence


class TestRecordUnderwriterDecision:
    def _to_under_review(self, db, case):
        _add_documents(db, case, OcrStatus.COMPLETED)
        submit_for_review(db, case, actor="officer@example.com")

    def test_wrong_status_is_rejected(self, db_session, case):
        with pytest.raises(TransitionNotAllowedError):
            record_underwriter_decision(
                db_session, case, CaseStatus.APPROVED, None, actor="uw@example.com"
            )

    def test_override_reason_required_when_no_summary_exists(self, db_session, case):
        self._to_under_review(db_session, case)
        with pytest.raises(DecisionError):
            record_underwriter_decision(
                db_session, case, CaseStatus.APPROVED, None, actor="uw@example.com"
            )

    def test_override_reason_required_when_decision_differs_from_recommendation(
        self, db_session, case
    ):
        self._to_under_review(db_session, case)
        db_session.add(
            CaseSummary(
                case_id=case.id,
                narrative_text="Looks fine.",
                recommendation=Recommendation.APPROVE,
                generated_by_model="fake",
                token_count=10,
                discrepancy_fingerprint="x",
            )
        )
        db_session.commit()

        with pytest.raises(DecisionError):
            record_underwriter_decision(
                db_session, case, CaseStatus.DENIED, None, actor="uw@example.com"
            )

    def test_accepting_recommendation_does_not_require_reason(self, db_session, case):
        self._to_under_review(db_session, case)
        db_session.add(
            CaseSummary(
                case_id=case.id,
                narrative_text="Looks fine.",
                recommendation=Recommendation.APPROVE,
                generated_by_model="fake",
                token_count=10,
                discrepancy_fingerprint="x",
            )
        )
        db_session.commit()

        result = record_underwriter_decision(
            db_session, case, CaseStatus.APPROVED, None, actor="uw@example.com"
        )
        assert result.status == CaseStatus.APPROVED

    def test_override_with_reason_succeeds_and_is_logged(self, db_session, case):
        self._to_under_review(db_session, case)
        db_session.add(
            CaseSummary(
                case_id=case.id,
                narrative_text="Looks fine.",
                recommendation=Recommendation.APPROVE,
                generated_by_model="fake",
                token_count=10,
                discrepancy_fingerprint="x",
            )
        )
        db_session.commit()

        result = record_underwriter_decision(
            db_session,
            case,
            CaseStatus.DENIED,
            "Applicant disclosed undocumented debt during phone verification.",
            actor="uw@example.com",
        )
        assert result.status == CaseStatus.DENIED

        entry = (
            db_session.query(AuditLog)
            .filter(AuditLog.case_id == case.id, AuditLog.action == "status_changed_to_denied")
            .one()
        )
        assert entry.actor == "uw@example.com"
        assert "undocumented debt" in entry.rule_or_evidence

    def test_referred_case_can_still_be_finalized(self, db_session, case):
        self._to_under_review(db_session, case)
        db_session.add(
            Discrepancy(
                case_id=case.id,
                field_name="income_paystub",
                stated_value="90000.00",
                document_value="80000.00",
                variance_pct=11.1,
                severity=DiscrepancySeverity.MINOR,
                source_document_id=None,
            )
        )
        db_session.commit()
        auto_route_case(db_session, case)  # -> referred
        assert case.status == CaseStatus.REFERRED

        result = record_underwriter_decision(
            db_session, case, CaseStatus.APPROVED, "Reviewed manually, looks fine.", actor="uw@example.com"
        )
        assert result.status == CaseStatus.APPROVED
