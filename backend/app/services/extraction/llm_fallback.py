"""LLM-assisted extraction fallback, used only for fields the deterministic
parser (`parsers.py`) couldn't find or found with low OCR confidence.

Only the OCR text is sent to the model, never the raw document image, to
keep token usage minimal. The response must be valid JSON matching a strict
per-document-type Pydantic schema; anything that fails validation is
rejected and logged, not silently trusted.
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, ValidationError

from backend.app.db.models.enums import DocumentType
from backend.app.services.extraction.parsers import ExtractedValue
from backend.app.services.llm.provider import complete_with_failover

logger = logging.getLogger("verity_mortgage")

LLM_FALLBACK_CONFIDENCE = 0.75  # fixed nominal confidence; the LLM has no per-field score


class PaystubLLMFields(BaseModel):
    employer_name: str | None = None
    gross_pay_current: float | None = None
    pay_frequency: str | None = None


class BankStatementLLMFields(BaseModel):
    beginning_balance: float | None = None
    ending_balance: float | None = None
    total_deposits: float | None = None
    total_withdrawals: float | None = None
    payroll_deposit_total: float | None = None


class W2LLMFields(BaseModel):
    employer_name: str | None = None
    employer_ein: str | None = None
    box1_wages: float | None = None


LLM_SCHEMAS: dict[DocumentType, type[BaseModel]] = {
    DocumentType.PAYSTUB: PaystubLLMFields,
    DocumentType.BANK_STATEMENT: BankStatementLLMFields,
    DocumentType.W2: W2LLMFields,
}


def _build_prompt(doc_type: DocumentType, ocr_text: str, field_names: list[str]) -> str:
    fields_list = ", ".join(field_names)
    return (
        f"You are extracting structured fields from OCR text of a {doc_type.value} "
        f"document. Return ONLY a JSON object with these exact keys: {fields_list}. "
        "Use null for any field you cannot find. Do not include any other keys or "
        "commentary.\n\nOCR TEXT:\n" + ocr_text
    )


def extract_missing_fields_via_llm(
    doc_type: DocumentType,
    ocr_text: str,
    missing_fields: set[str],
    complete_fn=complete_with_failover,
) -> dict[str, ExtractedValue]:
    """Ask an LLM to fill in `missing_fields` from the raw OCR text.

    Returns an empty dict (never raises) if no provider is configured, the
    call fails, or the response doesn't validate — the caller just keeps
    treating those fields as unresolved.
    """
    if not missing_fields:
        return {}

    schema_cls = LLM_SCHEMAS.get(doc_type)
    if schema_cls is None:
        return {}

    field_names = list(schema_cls.model_fields.keys())
    prompt = _build_prompt(doc_type, ocr_text, field_names)

    result = complete_fn(prompt)
    if result is None:
        logger.info(
            "llm_fallback_skipped",
            extra={"extra_fields": {"reason": "no_provider_configured", "doc_type": doc_type.value}},
        )
        return {}

    raw_text, provider_name = result
    try:
        data = json.loads(raw_text)
        parsed = schema_cls.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning(
            "llm_fallback_invalid_response",
            extra={
                "extra_fields": {
                    "provider": provider_name,
                    "doc_type": doc_type.value,
                    "error": str(exc),
                }
            },
        )
        return {}

    resolved: dict[str, ExtractedValue] = {}
    for field_name in missing_fields:
        value = getattr(parsed, field_name, None)
        if value is not None:
            resolved[field_name] = ExtractedValue(
                value=str(value), confidence=LLM_FALLBACK_CONFIDENCE, raw_text=f"llm:{provider_name}"
            )

    logger.info(
        "llm_fallback_resolved",
        extra={
            "extra_fields": {
                "provider": provider_name,
                "doc_type": doc_type.value,
                "resolved_fields": list(resolved.keys()),
            }
        },
    )
    return resolved
