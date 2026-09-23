from __future__ import annotations

import types
import uuid

from backend.app.db.models.enums import DiscrepancySeverity
from backend.app.services.summary.prompt import (
    build_prompt,
    build_retrieval_query,
)


def make_applicant():
    return types.SimpleNamespace(
        stated_income=100_000.0,
        stated_loan_amount=300_000.0,
        stated_property_value=340_000.0,
        stated_dti=36.0,
    )


def make_discrepancy(field_name="income_paystub", severity=DiscrepancySeverity.MINOR):
    return types.SimpleNamespace(
        field_name=field_name,
        severity=severity,
        stated_value="100000.00",
        document_value="85000.00",
        variance_pct=15.0,
    )


def make_chunk(text="## Income Verification Tolerance\nSome guidance text."):
    return types.SimpleNamespace(chunk_text=text)


class TestBuildRetrievalQuery:
    def test_no_discrepancies_gives_clean_case_query(self):
        query = build_retrieval_query([])
        assert "clean" in query.lower()

    def test_discrepancies_included_by_field_and_severity(self):
        query = build_retrieval_query([make_discrepancy("income_paystub", DiscrepancySeverity.MAJOR)])
        assert "income_paystub" in query
        assert "major" in query


class TestBuildPrompt:
    def test_includes_key_figures(self):
        prompt = build_prompt(make_applicant(), [], [])
        assert "$100,000.00" in prompt
        assert "$300,000.00" in prompt
        assert "36.00%" in prompt

    def test_includes_discrepancy_details(self):
        prompt = build_prompt(make_applicant(), [make_discrepancy()], [])
        assert "income_paystub" in prompt
        assert "minor" in prompt
        assert "85000.00" in prompt

    def test_no_discrepancies_says_none(self):
        prompt = build_prompt(make_applicant(), [], [])
        assert "None. All checked fields are within tolerance." in prompt

    def test_includes_retrieved_policy_chunks(self):
        prompt = build_prompt(make_applicant(), [], [make_chunk()])
        assert "Income Verification Tolerance" in prompt

    def test_never_includes_document_text_or_raw_ocr(self):
        # The prompt must stay limited to key figures + discrepancies +
        # retrieved guidance -- never full document/OCR text.
        prompt = build_prompt(make_applicant(), [make_discrepancy()], [])
        assert "raw_text_snippet" not in prompt
        assert "confidence_score" not in prompt

    def test_instructs_strict_json_response(self):
        prompt = build_prompt(make_applicant(), [], [])
        assert "JSON" in prompt
        assert "narrative" in prompt
        assert "recommendation" in prompt
