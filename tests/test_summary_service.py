from __future__ import annotations

import uuid

import pytest
from conftest import requires_db

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.case_summary import CaseSummary
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.enums import CaseStatus, DiscrepancySeverity
from backend.app.services.summary.service import (
    SummaryGenerationError,
    generate_case_summary,
)

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
        name="Summary Test Applicant",
        address="1 Test Way",
        employer_name="Test Employer",
        hmda_source_id=f"summary-test:{uuid.uuid4()}",
        stated_income=100_000,
        stated_loan_amount=300_000,
        stated_property_value=340_000,
        stated_dti=36,
    )
    db_session.add(applicant)
    db_session.flush()

    case = Case(applicant_id=applicant.id, status=CaseStatus.SUBMITTED)
    db_session.add(case)
    db_session.commit()

    applicant_id = applicant.id
    case_id = case.id

    yield case

    db = SessionLocal()
    db.query(CaseSummary).filter(CaseSummary.case_id == case_id).delete()
    db.query(Discrepancy).filter(Discrepancy.case_id == case_id).delete()
    db.query(Case).filter(Case.id == case_id).delete()
    db.query(Applicant).filter(Applicant.id == applicant_id).delete()
    db.commit()
    db.close()


def fake_complete_ok(prompt: str):
    return (
        '{"narrative": "Income and employer checks are consistent with the application.", "recommendation": "approve"}',
        "fake-provider",
        123,
    )


def fake_complete_deny(prompt: str):
    return (
        '{"narrative": "Income is materially overstated relative to the pay stub.", "recommendation": "deny"}',
        "fake-provider",
        150,
    )


class TestGenerateCaseSummary:
    def test_no_provider_configured_raises(self, db_session, case):
        with pytest.raises(SummaryGenerationError):
            generate_case_summary(db_session, case, complete_fn=lambda prompt: None)

    def test_successful_generation_persists_summary(self, db_session, case):
        summary = generate_case_summary(db_session, case, complete_fn=fake_complete_ok)
        assert summary.recommendation.value == "approve"
        assert summary.generated_by_model == "fake-provider"
        assert summary.token_count == 123
        assert "consistent" in summary.narrative_text

    def test_invalid_json_response_raises(self, db_session, case):
        with pytest.raises(SummaryGenerationError):
            generate_case_summary(db_session, case, complete_fn=lambda prompt: ("not json", "fake", 10))

    def test_invalid_recommendation_value_raises(self, db_session, case):
        def bad(prompt: str):
            return '{"narrative": "x", "recommendation": "maybe"}', "fake", 10

        with pytest.raises(SummaryGenerationError):
            generate_case_summary(db_session, case, complete_fn=bad)

    def test_rerun_with_unchanged_discrepancies_is_cached(self, db_session, case):
        first = generate_case_summary(db_session, case, complete_fn=fake_complete_ok)

        calls = []

        def tracking_complete(prompt: str):
            calls.append(prompt)
            return fake_complete_ok(prompt)

        second = generate_case_summary(db_session, case, complete_fn=tracking_complete)
        assert second.id == first.id
        assert calls == []  # cached: the LLM was never called again

    def test_force_regenerates_even_if_unchanged(self, db_session, case):
        first = generate_case_summary(db_session, case, complete_fn=fake_complete_ok)
        second = generate_case_summary(db_session, case, force=True, complete_fn=fake_complete_ok)
        assert second.id != first.id

    def test_new_discrepancy_triggers_regeneration(self, db_session, case):
        first = generate_case_summary(db_session, case, complete_fn=fake_complete_ok)

        db_session.add(
            Discrepancy(
                case_id=case.id,
                field_name="income_paystub",
                stated_value="100000.00",
                document_value="60000.00",
                variance_pct=40.0,
                severity=DiscrepancySeverity.MAJOR,
                source_document_id=None,
            )
        )
        db_session.commit()

        second = generate_case_summary(db_session, case, complete_fn=fake_complete_deny)
        assert second.id != first.id
        assert second.recommendation.value == "deny"
