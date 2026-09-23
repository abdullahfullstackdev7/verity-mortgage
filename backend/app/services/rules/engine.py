"""Cross-verification engine: pulls an applicant's stated figures and their
documents' extracted fields, runs them through the pure rules in
`rules.py`, and persists any out-of-tolerance result as a Discrepancy row.

Idempotent: re-running on a case that already has discrepancy rows is a
no-op unless `force=True` (mirrors the Phase 5 extraction pipeline).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.document import Document
from backend.app.db.models.document_embedding import DocumentEmbedding
from backend.app.db.models.enums import DocumentType, OcrStatus
from backend.app.db.models.extracted_field import ExtractedField
from backend.app.services.extraction.embedding import embed_text
from backend.app.services.rules.rules import (
    RuleResult,
    annualization_factor,
    check_bank_deposit,
    check_dti,
    check_employer_name,
    check_income,
)


def _latest_completed_document(db: Session, case_id: uuid.UUID, doc_type: DocumentType) -> Document | None:
    return (
        db.query(Document)
        .filter(
            Document.case_id == case_id,
            Document.doc_type == doc_type,
            Document.ocr_status == OcrStatus.COMPLETED,
        )
        .order_by(Document.uploaded_at.desc())
        .first()
    )


def _fields_by_name(db: Session, document_id: uuid.UUID) -> dict[str, ExtractedField]:
    rows = db.query(ExtractedField).filter(ExtractedField.document_id == document_id).all()
    return {row.field_name: row for row in rows}


def _embedding_for(db: Session, document_id: uuid.UUID, field_name: str) -> list[float] | None:
    row = (
        db.query(DocumentEmbedding)
        .filter(
            DocumentEmbedding.document_id == document_id,
            DocumentEmbedding.field_name == field_name,
        )
        .one_or_none()
    )
    return list(row.embedding) if row is not None else None


def _existing_discrepancies(db: Session, case_id: uuid.UUID) -> list[Discrepancy]:
    return db.query(Discrepancy).filter(Discrepancy.case_id == case_id).all()


def _evaluate(db: Session, case: Case, applicant: Applicant) -> list[RuleResult]:
    results: list[RuleResult] = []
    stated_income = float(applicant.stated_income)

    paystub_income: float | None = None
    paystub_doc = _latest_completed_document(db, case.id, DocumentType.PAYSTUB)
    if paystub_doc is not None:
        fields = _fields_by_name(db, paystub_doc.id)
        gross_field = fields.get("gross_pay_current")
        if gross_field is not None:
            factor = annualization_factor(
                fields["pay_frequency"].extracted_value if "pay_frequency" in fields else None
            )
            paystub_income = float(gross_field.extracted_value) * factor
            result = check_income(stated_income, paystub_income, "income_paystub", paystub_doc.id)
            if result:
                results.append(result)

        employer_field = fields.get("employer_name")
        if employer_field is not None:
            extracted_embedding = _embedding_for(db, paystub_doc.id, "employer_name")
            if extracted_embedding is not None:
                stated_embedding = embed_text(applicant.employer_name)
                result = check_employer_name(
                    applicant.employer_name,
                    employer_field.extracted_value,
                    stated_embedding,
                    extracted_embedding,
                    "employer_name_paystub",
                    paystub_doc.id,
                )
                if result:
                    results.append(result)

    w2_doc = _latest_completed_document(db, case.id, DocumentType.W2)
    if w2_doc is not None:
        fields = _fields_by_name(db, w2_doc.id)
        box1_field = fields.get("box1_wages")
        if box1_field is not None:
            result = check_income(
                stated_income, float(box1_field.extracted_value), "income_w2", w2_doc.id
            )
            if result:
                results.append(result)

        employer_field = fields.get("employer_name")
        if employer_field is not None:
            extracted_embedding = _embedding_for(db, w2_doc.id, "employer_name")
            if extracted_embedding is not None:
                stated_embedding = embed_text(applicant.employer_name)
                result = check_employer_name(
                    applicant.employer_name,
                    employer_field.extracted_value,
                    stated_embedding,
                    extracted_embedding,
                    "employer_name_w2",
                    w2_doc.id,
                )
                if result:
                    results.append(result)

    bank_doc = _latest_completed_document(db, case.id, DocumentType.BANK_STATEMENT)
    if bank_doc is not None:
        fields = _fields_by_name(db, bank_doc.id)
        deposit_field = fields.get("payroll_deposit_total")
        if deposit_field is not None:
            result = check_bank_deposit(
                stated_income, float(deposit_field.extracted_value), bank_doc.id
            )
            if result:
                results.append(result)

    if paystub_income is not None and paystub_doc is not None:
        result = check_dti(stated_income, float(applicant.stated_dti), paystub_income, paystub_doc.id)
        if result:
            results.append(result)

    return results


def run_verification(db: Session, case: Case, force: bool = False) -> list[Discrepancy]:
    existing = _existing_discrepancies(db, case.id)
    if existing and not force:
        return existing

    if existing:
        db.query(Discrepancy).filter(Discrepancy.case_id == case.id).delete()
        db.commit()

    applicant = db.get(Applicant, case.applicant_id)
    results = _evaluate(db, case, applicant)

    discrepancies: list[Discrepancy] = []
    for result in results:
        row = Discrepancy(
            case_id=case.id,
            field_name=result.field_name,
            stated_value=result.stated_value,
            document_value=result.document_value,
            variance_pct=result.variance_pct,
            severity=result.severity,
            source_document_id=result.source_document_id,
        )
        db.add(row)
        discrepancies.append(row)

    db.commit()
    for row in discrepancies:
        db.refresh(row)

    return discrepancies
