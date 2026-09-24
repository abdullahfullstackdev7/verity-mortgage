"""Extraction service: OCR -> deterministic parse -> LLM fallback for
missing/low-confidence required fields -> embeddings -> persistence.

Idempotent: re-running on a document that already has extracted_fields rows
is a no-op unless `force=True`.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.models.document import Document
from backend.app.db.models.document_embedding import DocumentEmbedding
from backend.app.db.models.enums import OcrStatus
from backend.app.db.models.extracted_field import ExtractedField
from backend.app.services.extraction.embedding import embed_text
from backend.app.services.extraction.llm_fallback import extract_missing_fields_via_llm
from backend.app.services.extraction.ocr import full_text, run_ocr
from backend.app.services.extraction.parsers import (
    FIELD_CONFIDENCE_THRESHOLD,
    PARSERS,
    REQUIRED_FIELDS,
    ExtractedValue,
)

# Text-valued fields worth embedding for later fuzzy matching (e.g. an
# employer name spelled slightly differently between two documents).
EMBEDDABLE_FIELDS = {"employer_name"}

RAW_TEXT_SNIPPET_MAX_LEN = 1000


class ExtractionError(Exception):
    pass


def _existing_fields(db: Session, document_id) -> list[ExtractedField]:
    return db.query(ExtractedField).filter(ExtractedField.document_id == document_id).all()


def _clear_previous_results(db: Session, document_id) -> None:
    db.query(ExtractedField).filter(ExtractedField.document_id == document_id).delete()
    db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == document_id).delete()


def extract_document(db: Session, document: Document, force: bool = False) -> list[ExtractedField]:
    existing = _existing_fields(db, document.id)
    if existing and not force:
        return existing

    if existing:
        _clear_previous_results(db, document.id)
        db.commit()

    document.ocr_status = OcrStatus.PROCESSING
    db.commit()

    try:
        page = run_ocr(Path(document.file_path))
    except Exception as exc:
        document.ocr_status = OcrStatus.FAILED
        db.commit()
        raise ExtractionError(f"OCR failed for document {document.id}: {exc}") from exc

    parser = PARSERS.get(document.doc_type)
    parsed: dict[str, ExtractedValue] = parser(page) if parser else {}

    required = REQUIRED_FIELDS.get(document.doc_type, set())
    unresolved = {
        name for name in required if name not in parsed or parsed[name].confidence < FIELD_CONFIDENCE_THRESHOLD
    }

    if unresolved:
        llm_values = extract_missing_fields_via_llm(document.doc_type, full_text(page), unresolved)
        parsed.update(llm_values)

    extracted_fields: list[ExtractedField] = []
    for field_name, value in parsed.items():
        field = ExtractedField(
            document_id=document.id,
            field_name=field_name,
            extracted_value=value.value,
            confidence_score=value.confidence,
            raw_text_snippet=value.raw_text[:RAW_TEXT_SNIPPET_MAX_LEN],
        )
        db.add(field)
        extracted_fields.append(field)

    for field_name in EMBEDDABLE_FIELDS & parsed.keys():
        value_text = parsed[field_name].value
        vector = embed_text(value_text)
        db.add(
            DocumentEmbedding(
                document_id=document.id,
                field_name=field_name,
                value_text=value_text,
                embedding=vector,
            )
        )

    document.ocr_status = OcrStatus.COMPLETED
    try:
        db.commit()
    except IntegrityError:
        # A concurrent call for the same document (e.g. a double-click, or
        # two requests racing the check-then-insert idempotency check above)
        # already committed its own rows first; the unique constraint on
        # (document_id, field_name) rejects this one. Fall back to whatever
        # that other call persisted, rather than surfacing a 500.
        db.rollback()
        return _existing_fields(db, document.id)
    for field in extracted_fields:
        db.refresh(field)

    return extracted_fields
