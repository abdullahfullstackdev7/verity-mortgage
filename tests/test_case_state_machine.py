from __future__ import annotations

import uuid

import pytest
from conftest import requires_db

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.audit_log import AuditLog
from backend.app.db.models.case import Case
from backend.app.db.models.document import Document
from backend.app.db.models.enums import CaseStatus, DocumentType, OcrStatus
from backend.app.services.case_state_machine import (
    ALLOWED_TRANSITIONS,
    TransitionNotAllowedError,
    can_transition,
    check_required_documents_extracted,
    check_required_documents_present,
    transition_case,
)


class TestAllowedTransitionsTable:
    def test_submitted_can_only_reach_documents_pending(self):
        assert can_transition(CaseStatus.SUBMITTED, CaseStatus.DOCUMENTS_PENDING)
        assert not can_transition(CaseStatus.SUBMITTED, CaseStatus.UNDER_REVIEW)
        assert not can_transition(CaseStatus.SUBMITTED, CaseStatus.APPROVED)

    def test_documents_pending_can_only_reach_under_review(self):
        assert can_transition(CaseStatus.DOCUMENTS_PENDING, CaseStatus.UNDER_REVIEW)
        assert not can_transition(CaseStatus.DOCUMENTS_PENDING, CaseStatus.APPROVED)

    def test_under_review_can_reach_all_three_decisions(self):
        for target in (CaseStatus.APPROVED, CaseStatus.REFERRED, CaseStatus.DENIED):
            assert can_transition(CaseStatus.UNDER_REVIEW, target)

    def test_referred_can_be_finalized_but_not_sent_back(self):
        assert can_transition(CaseStatus.REFERRED, CaseStatus.APPROVED)
        assert can_transition(CaseStatus.REFERRED, CaseStatus.DENIED)
        assert not can_transition(CaseStatus.REFERRED, CaseStatus.UNDER_REVIEW)
        assert not can_transition(CaseStatus.REFERRED, CaseStatus.REFERRED)

    def test_approved_and_denied_are_terminal(self):
        assert ALLOWED_TRANSITIONS[CaseStatus.APPROVED] == set()
        assert ALLOWED_TRANSITIONS[CaseStatus.DENIED] == set()

    def test_every_status_has_an_entry(self):
        assert set(ALLOWED_TRANSITIONS.keys()) == set(CaseStatus)


@requires_db
class TestGuardsAndTransitionCase:
    @pytest.fixture
    def case(self):
        db = SessionLocal()
        applicant = Applicant(
            id=uuid.uuid4(),
            name="State Machine Test",
            address="1 Test Way",
            employer_name="Test Employer",
            hmda_source_id=f"state-machine-test:{uuid.uuid4()}",
            stated_income=90000,
            stated_loan_amount=300000,
            stated_property_value=340000,
            stated_dti=32,
        )
        db.add(applicant)
        db.flush()
        case = Case(applicant_id=applicant.id, status=CaseStatus.SUBMITTED)
        db.add(case)
        db.commit()
        applicant_id, case_id = applicant.id, case.id
        db.close()

        yield case_id

        db = SessionLocal()
        db.query(AuditLog).filter(AuditLog.case_id == case_id).delete()
        db.query(Document).filter(Document.case_id == case_id).delete()
        db.query(Case).filter(Case.id == case_id).delete()
        db.query(Applicant).filter(Applicant.id == applicant_id).delete()
        db.commit()
        db.close()

    def test_documents_present_guard_fails_when_missing(self, case):
        db = SessionLocal()
        c = db.get(Case, case)
        ok, reason = check_required_documents_present(db, c)
        assert not ok
        assert "paystub" in reason
        db.close()

    def test_documents_present_guard_passes_once_all_three_uploaded(self, case):
        db = SessionLocal()
        c = db.get(Case, case)
        for doc_type in (DocumentType.PAYSTUB, DocumentType.BANK_STATEMENT, DocumentType.W2):
            db.add(
                Document(
                    case_id=c.id,
                    doc_type=doc_type,
                    file_path=f"/fake/{doc_type.value}.pdf",
                    ocr_status=OcrStatus.PENDING_OCR,
                )
            )
        db.commit()

        ok, _reason = check_required_documents_present(db, c)
        assert ok
        db.close()

    def test_documents_extracted_guard_requires_completed_ocr_status(self, case):
        db = SessionLocal()
        c = db.get(Case, case)
        for doc_type in (DocumentType.PAYSTUB, DocumentType.BANK_STATEMENT, DocumentType.W2):
            db.add(
                Document(
                    case_id=c.id,
                    doc_type=doc_type,
                    file_path=f"/fake/{doc_type.value}.pdf",
                    ocr_status=OcrStatus.PENDING_OCR,  # present, but not extracted
                )
            )
        db.commit()

        ok, _reason = check_required_documents_extracted(db, c)
        assert not ok

        db.query(Document).filter(Document.case_id == c.id).update({Document.ocr_status: OcrStatus.COMPLETED})
        db.commit()

        ok, _reason = check_required_documents_extracted(db, c)
        assert ok
        db.close()

    def test_transition_case_writes_audit_log_entry(self, case):
        db = SessionLocal()
        c = db.get(Case, case)
        transition_case(db, c, CaseStatus.DOCUMENTS_PENDING, "test-actor", "test evidence")

        assert c.status == CaseStatus.DOCUMENTS_PENDING
        entries = db.query(AuditLog).filter(AuditLog.case_id == c.id).all()
        assert len(entries) == 1
        assert entries[0].actor == "test-actor"
        assert entries[0].action == "status_changed_to_documents_pending"
        assert entries[0].rule_or_evidence == "test evidence"
        db.close()

    def test_transition_case_rejects_disallowed_edge(self, case):
        db = SessionLocal()
        c = db.get(Case, case)
        with pytest.raises(TransitionNotAllowedError):
            transition_case(db, c, CaseStatus.APPROVED, "test-actor", "skip ahead")
        assert c.status == CaseStatus.SUBMITTED  # unchanged
        db.close()
