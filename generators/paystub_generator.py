"""Generate a synthetic pay stub PDF for one HMDA-derived applicant record.

The stub's annualized income is derived from the applicant's stated HMDA
income, run through the deterministic discrepancy injector in
`discrepancy.py`, and split into a biweekly gross/net breakdown with
representative tax withholding rates. None of the figures are drawn from
real payroll data.
"""

from __future__ import annotations

import datetime as dt
import random
from pathlib import Path

from generators import discrepancy
from generators.identity import Identity
from generators.render import render_pdf

TEMPLATE_NAME = "paystub_template.html"
PAY_PERIODS_PER_YEAR = 26

# Fixed reference year used to lay out pay periods, kept constant (rather
# than tied to wall-clock "today") so regenerating documents is reproducible.
ANCHOR_YEAR = 2024

FEDERAL_TAX_RATE = 0.12
STATE_TAX_RATE = 0.04
SOCIAL_SECURITY_RATE = 0.062
MEDICARE_RATE = 0.0145


def _period_index_for(applicant_id: str) -> int:
    """Deterministically pick how many pay periods have elapsed this year."""
    rng = random.Random(int.from_bytes(applicant_id.encode()[:8], "little", signed=False))
    return rng.randint(8, PAY_PERIODS_PER_YEAR)


def _pay_period_dates(period_index: int) -> tuple[dt.date, dt.date, dt.date]:
    year_start = dt.date(ANCHOR_YEAR, 1, 1)
    period_start = year_start + dt.timedelta(days=14 * (period_index - 1))
    period_end = period_start + dt.timedelta(days=13)
    pay_date = period_end + dt.timedelta(days=5)
    return period_start, period_end, pay_date


def build_context(
    applicant_id: str, stated_income: float, identity: Identity
) -> dict:
    document_income, decision = discrepancy.apply_income_discrepancy(
        stated_income, applicant_id
    )

    period_index = _period_index_for(applicant_id)
    period_start, period_end, pay_date = _pay_period_dates(period_index)

    gross_pay = round(document_income / PAY_PERIODS_PER_YEAR, 2)
    ytd_gross = round(gross_pay * period_index, 2)

    federal_tax = round(gross_pay * FEDERAL_TAX_RATE, 2)
    state_tax = round(gross_pay * STATE_TAX_RATE, 2)
    social_security = round(gross_pay * SOCIAL_SECURITY_RATE, 2)
    medicare = round(gross_pay * MEDICARE_RATE, 2)
    net_pay = round(gross_pay - federal_tax - state_tax - social_security - medicare, 2)

    ytd_federal_tax = round(ytd_gross * FEDERAL_TAX_RATE, 2)
    ytd_state_tax = round(ytd_gross * STATE_TAX_RATE, 2)
    ytd_social_security = round(ytd_gross * SOCIAL_SECURITY_RATE, 2)
    ytd_medicare = round(ytd_gross * MEDICARE_RATE, 2)
    ytd_net_pay = round(
        ytd_gross - ytd_federal_tax - ytd_state_tax - ytd_social_security - ytd_medicare, 2
    )

    context = {
        "employer_name": identity.employer_name,
        "employer_address": identity.employer_address,
        "employee_name": identity.full_name,
        "employee_address": identity.address_line,
        "ssn_masked": identity.ssn_masked,
        "employee_id": identity.employee_id,
        "pay_period_start": period_start.isoformat(),
        "pay_period_end": period_end.isoformat(),
        "pay_date": pay_date.isoformat(),
        "pay_frequency": "Biweekly",
        "gross_pay": gross_pay,
        "ytd_gross": ytd_gross,
        "federal_tax": federal_tax,
        "state_tax": state_tax,
        "social_security": social_security,
        "medicare": medicare,
        "net_pay": net_pay,
        "ytd_federal_tax": ytd_federal_tax,
        "ytd_state_tax": ytd_state_tax,
        "ytd_social_security": ytd_social_security,
        "ytd_medicare": ytd_medicare,
        "ytd_net_pay": ytd_net_pay,
    }
    return context, document_income, decision


def generate(
    applicant_id: str,
    stated_income: float,
    identity: Identity,
    output_path: Path,
) -> tuple[float, discrepancy.DiscrepancyDecision]:
    """Render the pay stub PDF and return (document_income, decision) so the
    caller can record ground truth for injected discrepancies."""
    context, document_income, decision = build_context(applicant_id, stated_income, identity)
    render_pdf(TEMPLATE_NAME, context, output_path)
    return document_income, decision
