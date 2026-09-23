"""Generate a synthetic W-2 PDF for one applicant.

Box 1 wages are set directly from the applicant's stated HMDA income (the
discrepancy injector in this phase only targets the pay stub, per the
project plan's example), so the W-2 and bank statement act as the clean
cross-check documents against which the pay stub is later verified.
"""

from __future__ import annotations

from pathlib import Path

from generators.identity import Identity
from generators.render import render_pdf

TEMPLATE_NAME = "w2_template.html"
ANCHOR_YEAR = 2024

FEDERAL_TAX_RATE = 0.12
STATE_TAX_RATE = 0.04
SOCIAL_SECURITY_RATE = 0.062
MEDICARE_RATE = 0.0145


def build_context(stated_income: float, identity: Identity) -> dict:
    box1_wages = round(stated_income, 2)
    box2_fed_tax_withheld = round(box1_wages * FEDERAL_TAX_RATE, 2)
    box3_ss_wages = box1_wages
    box4_ss_tax = round(box1_wages * SOCIAL_SECURITY_RATE, 2)
    box5_medicare_wages = box1_wages
    box6_medicare_tax = round(box1_wages * MEDICARE_RATE, 2)
    box16_state_wages = box1_wages
    box17_state_tax = round(box1_wages * STATE_TAX_RATE, 2)

    context = {
        "tax_year": ANCHOR_YEAR,
        "employer_name": identity.employer_name,
        "employer_ein": identity.employer_ein,
        "employer_address": identity.employer_address,
        "employee_name": identity.full_name,
        "employee_ssn_masked": identity.ssn_masked,
        "employee_address": identity.address_line,
        "box1_wages": box1_wages,
        "box2_fed_tax_withheld": box2_fed_tax_withheld,
        "box3_ss_wages": box3_ss_wages,
        "box4_ss_tax": box4_ss_tax,
        "box5_medicare_wages": box5_medicare_wages,
        "box6_medicare_tax": box6_medicare_tax,
        "state": identity.state_abbr,
        "box16_state_wages": box16_state_wages,
        "box17_state_tax": box17_state_tax,
    }
    return context


def generate(stated_income: float, identity: Identity, output_path: Path) -> None:
    context = build_context(stated_income, identity)
    render_pdf(TEMPLATE_NAME, context, output_path)
