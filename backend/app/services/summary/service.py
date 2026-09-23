"""Underwriter summary generation: exactly one LLM call per case, with
Groq-then-Gemini failover, a single deterministic prompt template, and
full token accounting logged per case.

Caching: a case's summary is only regenerated if its discrepancy set has
changed since the last generation (tracked via a fingerprint hash), so
reloading a case in the UI never triggers a repeat LLM call.
"""

from __future__ import annotations

import hashlib
import json
import logging

from typing import Literal

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.case_summary import CaseSummary
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.enums import Recommendation
from backend.app.services.llm import provider as llm_provider
from backend.app.services.policy.retrieval import retrieve_relevant_chunks
from backend.app.services.summary.prompt import build_prompt, build_retrieval_query

logger = logging.getLogger("verity_mortgage")


class SummaryGenerationError(Exception):
    pass


class SummaryLLMOutput(BaseModel):
    narrative: str
    recommendation: Literal["approve", "refer", "deny"]


def compute_discrepancy_fingerprint(discrepancies: list[Discrepancy]) -> str:
    """Deterministic hash of a case's current discrepancy set, independent
    of row insertion order or ids."""
    normalized = sorted(
        (d.field_name, d.severity.value, str(d.variance_pct)) for d in discrepancies
    )
    payload = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _latest_summary(db: Session, case_id) -> CaseSummary | None:
    return (
        db.query(CaseSummary)
        .filter(CaseSummary.case_id == case_id)
        .order_by(CaseSummary.created_at.desc())
        .first()
    )


def generate_case_summary(
    db: Session,
    case: Case,
    force: bool = False,
    complete_fn=None,
) -> CaseSummary:
    # Resolved at call time (not bound as a default at import time) so
    # tests can monkeypatch `llm_provider.complete_with_usage_and_failover`
    # and have it take effect even when called through the API layer.
    if complete_fn is None:
        complete_fn = llm_provider.complete_with_usage_and_failover

    discrepancies = db.query(Discrepancy).filter(Discrepancy.case_id == case.id).all()
    fingerprint = compute_discrepancy_fingerprint(discrepancies)

    existing = _latest_summary(db, case.id)
    if existing is not None and not force and existing.discrepancy_fingerprint == fingerprint:
        return existing

    applicant = db.get(Applicant, case.applicant_id)

    query_text = build_retrieval_query(discrepancies)
    policy_chunks = retrieve_relevant_chunks(db, query_text)

    prompt = build_prompt(applicant, discrepancies, policy_chunks)

    result = complete_fn(prompt)
    if result is None:
        logger.warning(
            "summary_generation_failed",
            extra={"extra_fields": {"case_id": str(case.id), "reason": "no_provider_configured"}},
        )
        raise SummaryGenerationError(
            "No LLM provider is configured (set GROQ_API_KEY or GEMINI_API_KEY)."
        )

    raw_text, provider_name, token_count = result

    try:
        data = json.loads(raw_text)
        parsed = SummaryLLMOutput.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning(
            "summary_generation_invalid_response",
            extra={
                "extra_fields": {
                    "case_id": str(case.id),
                    "provider": provider_name,
                    "error": str(exc),
                }
            },
        )
        raise SummaryGenerationError(
            f"LLM response from {provider_name} did not match the expected schema"
        ) from exc

    summary = CaseSummary(
        case_id=case.id,
        narrative_text=parsed.narrative,
        recommendation=Recommendation(parsed.recommendation),
        generated_by_model=provider_name,
        token_count=token_count,
        discrepancy_fingerprint=fingerprint,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    logger.info(
        "summary_generated",
        extra={
            "extra_fields": {
                "case_id": str(case.id),
                "provider": provider_name,
                "token_count": token_count,
                "recommendation": parsed.recommendation,
            }
        },
    )

    return summary
