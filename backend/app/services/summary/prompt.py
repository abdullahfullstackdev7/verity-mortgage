"""Builds the single, compact prompt sent for a case's underwriter summary.

Token-minimization is the point: this sends the applicant's key figures,
the flagged discrepancies (never full document text or the full
application record), and only the top retrieved policy guideline chunks
-- not the whole guidelines corpus.
"""

from __future__ import annotations

from backend.app.db.models.applicant import Applicant
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.policy_chunk import PolicyChunk

RESPONSE_INSTRUCTIONS = (
    "Respond with ONLY a JSON object of the form "
    '{"narrative": "<3-5 sentence factual summary>", '
    '"recommendation": "approve" | "refer" | "deny"}. '
    "No text outside the JSON object."
)


def build_retrieval_query(discrepancies: list[Discrepancy]) -> str:
    if not discrepancies:
        return "clean case with no discrepancies, straightforward approval"
    return "; ".join(f"{d.field_name} {d.severity.value} discrepancy" for d in discrepancies)


def _format_discrepancies(discrepancies: list[Discrepancy]) -> str:
    if not discrepancies:
        return "None. All checked fields are within tolerance."
    lines = []
    for d in discrepancies:
        lines.append(
            f"- {d.field_name} ({d.severity.value}): stated={d.stated_value}, "
            f"document={d.document_value}, variance={d.variance_pct}%"
        )
    return "\n".join(lines)


def _format_policy_chunks(chunks: list[PolicyChunk]) -> str:
    if not chunks:
        return "None retrieved."
    return "\n\n".join(chunk.chunk_text for chunk in chunks)


def build_prompt(applicant: Applicant, discrepancies: list[Discrepancy], policy_chunks: list[PolicyChunk]) -> str:
    return (
        "You are drafting a factual underwriting summary for a loan case. "
        "Base the narrative only on the figures and discrepancies below; do "
        "not invent details.\n\n"
        "APPLICANT KEY FIGURES\n"
        f"Stated income: ${float(applicant.stated_income):,.2f}\n"
        f"Stated loan amount: ${float(applicant.stated_loan_amount):,.2f}\n"
        f"Stated property value: ${float(applicant.stated_property_value):,.2f}\n"
        f"Stated debt-to-income ratio: {float(applicant.stated_dti):.2f}%\n\n"
        "FLAGGED DISCREPANCIES\n"
        f"{_format_discrepancies(discrepancies)}\n\n"
        "RELEVANT INTERNAL GUIDANCE\n"
        f"{_format_policy_chunks(policy_chunks)}\n\n"
        f"{RESPONSE_INSTRUCTIONS}"
    )
