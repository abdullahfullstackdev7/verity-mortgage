"""Pure, deterministic cross-verification rules. No database access, no LLM
calls — every function here takes plain primitives and returns a RuleResult
or None. The engine (`engine.py`) is responsible for pulling ORM data into
these primitives and persisting the results.

Tolerance model: each check defines a "clean" band (no discrepancy at all)
and a "major" cutoff beyond the clean band; anything in between is "minor".
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from backend.app.db.models.enums import DiscrepancySeverity
from backend.app.services.rules.similarity import cosine_similarity

# Income: percentage variance between an extracted, document-derived annual
# income figure and the applicant's stated HMDA income.
INCOME_CLEAN_PCT = 10.0
INCOME_MAJOR_PCT = 20.0

# Employer name: cosine similarity between sentence-embeddings of the
# stated and extracted employer name (see Phase 5's document_embeddings).
EMPLOYER_CLEAN_SIMILARITY = 0.85
EMPLOYER_MAJOR_SIMILARITY = 0.60

# Bank deposits: percentage variance between the sum of paycheck-looking
# deposits on the statement and the expected net income for that statement
# period, derived from the applicant's stated gross income.
BANK_DEPOSIT_CLEAN_PCT = 15.0
BANK_DEPOSIT_MAJOR_PCT = 30.0

# The same payroll tax model used by the Phase 2 document generators
# (generators/paystub_generator.py), reused here so the expected net
# deposit figure is internally consistent with how the demo data was
# generated. A production system would instead use jurisdiction-specific
# tax tables; this is a deliberate, documented simplification.
FEDERAL_TAX_RATE = 0.12
STATE_TAX_RATE = 0.04
SOCIAL_SECURITY_RATE = 0.062
MEDICARE_RATE = 0.0145
COMBINED_TAX_RATE = FEDERAL_TAX_RATE + STATE_TAX_RATE + SOCIAL_SECURITY_RATE + MEDICARE_RATE

# Bank statements only cover roughly a calendar month, and Phase 5's OCR
# parser does not currently extract the statement period dates (only
# balances and deposit lines, per the Phase 5 plan). A nominal 30-day
# period is a documented simplifying assumption.
NOMINAL_STATEMENT_PERIOD_DAYS = 30.0

# Annualization factors for pay stub gross-pay figures, keyed by the
# extracted `pay_frequency` text (lowercased). Falls back to biweekly,
# the only frequency the Phase 2 generator currently produces.
PAY_FREQUENCY_ANNUALIZATION: dict[str, int] = {
    "weekly": 52,
    "biweekly": 26,
    "semimonthly": 24,
    "monthly": 12,
}
DEFAULT_ANNUALIZATION_FACTOR = 26

# Debt-to-income: absolute percentage-point difference between the
# HMDA-stated DTI and a DTI recomputed by holding the implied monthly debt
# obligation fixed and substituting the extracted (verified) income.
DTI_CLEAN_PP = 3.0
DTI_MAJOR_PP = 6.0


@dataclass(frozen=True)
class RuleResult:
    field_name: str
    stated_value: str
    document_value: str
    variance_pct: float
    severity: DiscrepancySeverity
    source_document_id: uuid.UUID | None


def _classify(variance: float, clean: float, major: float) -> DiscrepancySeverity | None:
    if variance <= clean:
        return None
    if variance <= major:
        return DiscrepancySeverity.MINOR
    return DiscrepancySeverity.MAJOR


def annualization_factor(pay_frequency: str | None) -> int:
    if not pay_frequency:
        return DEFAULT_ANNUALIZATION_FACTOR
    return PAY_FREQUENCY_ANNUALIZATION.get(pay_frequency.strip().lower(), DEFAULT_ANNUALIZATION_FACTOR)


def check_income(
    stated_income: float,
    extracted_income: float,
    field_name: str,
    source_document_id: uuid.UUID | None,
) -> RuleResult | None:
    if stated_income <= 0 or extracted_income < 0:
        return None

    variance_pct = abs(extracted_income - stated_income) / stated_income * 100
    severity = _classify(variance_pct, INCOME_CLEAN_PCT, INCOME_MAJOR_PCT)
    if severity is None:
        return None

    return RuleResult(
        field_name=field_name,
        stated_value=f"{stated_income:.2f}",
        document_value=f"{extracted_income:.2f}",
        variance_pct=round(variance_pct, 2),
        severity=severity,
        source_document_id=source_document_id,
    )


def check_employer_name(
    stated_name: str,
    extracted_name: str,
    stated_embedding: list[float],
    extracted_embedding: list[float],
    field_name: str,
    source_document_id: uuid.UUID | None,
) -> RuleResult | None:
    if not stated_name or not extracted_name:
        return None

    similarity = cosine_similarity(stated_embedding, extracted_embedding)
    if similarity >= EMPLOYER_CLEAN_SIMILARITY:
        return None

    severity = (
        DiscrepancySeverity.MAJOR
        if similarity < EMPLOYER_MAJOR_SIMILARITY
        else DiscrepancySeverity.MINOR
    )
    variance_pct = round((1 - similarity) * 100, 2)

    return RuleResult(
        field_name=field_name,
        stated_value=stated_name,
        document_value=extracted_name,
        variance_pct=variance_pct,
        severity=severity,
        source_document_id=source_document_id,
    )


def check_bank_deposit(
    stated_income: float,
    payroll_deposit_total: float,
    source_document_id: uuid.UUID | None,
    statement_period_days: float = NOMINAL_STATEMENT_PERIOD_DAYS,
) -> RuleResult | None:
    if stated_income <= 0 or payroll_deposit_total < 0:
        return None

    expected_net_annual_income = stated_income * (1 - COMBINED_TAX_RATE)
    expected_deposit = expected_net_annual_income * (statement_period_days / 365)
    if expected_deposit <= 0:
        return None

    variance_pct = abs(payroll_deposit_total - expected_deposit) / expected_deposit * 100
    severity = _classify(variance_pct, BANK_DEPOSIT_CLEAN_PCT, BANK_DEPOSIT_MAJOR_PCT)
    if severity is None:
        return None

    return RuleResult(
        field_name="bank_deposit_total",
        stated_value=f"{expected_deposit:.2f}",
        document_value=f"{payroll_deposit_total:.2f}",
        variance_pct=round(variance_pct, 2),
        severity=severity,
        source_document_id=source_document_id,
    )


def check_dti(
    stated_income: float,
    stated_dti: float,
    extracted_income: float,
    source_document_id: uuid.UUID | None,
) -> RuleResult | None:
    if stated_income <= 0 or extracted_income <= 0 or stated_dti < 0:
        return None

    implied_monthly_debt = (stated_dti / 100) * (stated_income / 12)
    extracted_monthly_income = extracted_income / 12
    recomputed_dti = implied_monthly_debt / extracted_monthly_income * 100

    diff_pp = abs(recomputed_dti - stated_dti)
    severity = _classify(diff_pp, DTI_CLEAN_PP, DTI_MAJOR_PP)
    if severity is None:
        return None

    return RuleResult(
        field_name="debt_to_income_ratio",
        stated_value=f"{stated_dti:.2f}",
        document_value=f"{recomputed_dti:.2f}",
        variance_pct=round(diff_pp, 2),
        severity=severity,
        source_document_id=source_document_id,
    )
