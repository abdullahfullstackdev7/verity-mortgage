"""Validate the full pipeline's discrepancy classification against Phase 2's
target distribution, at a scale beyond the ~6-row demo sample.

Real HMDA data can't be downloaded in this environment, so this generates a
synthetic applicant pool (realistic income/loan/DTI figures, not derived
from real records) rather than loading one. For each applicant it: renders a
pay stub PDF through Phase 2's discrepancy injector, runs it through the
real OCR extraction pipeline (Phase 5) and the rules engine (Phase 6), and
classifies the resulting case as clean / minor / major based on the
discrepancies the engine actually found -- not the injector's ground truth
directly, since OCR noise and boundary cases can shift a case's classified
severity even when the injector's decision was clean or vice versa. That
gap between "what was injected" and "what the pipeline concludes" is what
this script is checking.

    uv run python -m scripts.validate_demo_dataset --count 150
"""

from __future__ import annotations

import argparse
import random
import tempfile
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.db.base import SessionLocal
from backend.app.db.models.applicant import Applicant
from backend.app.db.models.case import Case
from backend.app.db.models.discrepancy import Discrepancy
from backend.app.db.models.document import Document
from backend.app.db.models.document_embedding import DocumentEmbedding
from backend.app.db.models.enums import CaseStatus, DiscrepancySeverity, DocumentType, OcrStatus
from backend.app.db.models.extracted_field import ExtractedField
from backend.app.services.extraction.pipeline import extract_document
from backend.app.services.rules.engine import run_verification
from generators.discrepancy import DiscrepancyDecision
from generators.identity import build_identity
from generators.paystub_generator import generate as generate_paystub

MARKER_PREFIX = "validation-demo"
RNG_SEED = 20260923


def _synthetic_applicant(index: int, tmp_dir: Path) -> tuple[Applicant, DiscrepancyDecision, str, Path]:
    rng = random.Random(f"{RNG_SEED}:{index}")
    applicant_id_str = f"{MARKER_PREFIX}-{index}"
    income = round(rng.uniform(45_000, 220_000), 2)

    identity = build_identity(applicant_id_str)
    applicant = Applicant(
        id=uuid.uuid5(uuid.NAMESPACE_URL, applicant_id_str),
        name=identity.full_name,
        address=identity.address_line,
        employer_name=identity.employer_name,
        hmda_source_id=f"{MARKER_PREFIX}:{applicant_id_str}",
        stated_income=income,
        stated_loan_amount=round(income * rng.uniform(2.5, 4.5), -3),
        stated_property_value=round(income * rng.uniform(3.0, 5.5), -3),
        stated_dti=round(rng.uniform(18, 42), 1),
    )

    pdf_path = tmp_dir / f"{applicant_id_str}.pdf"
    _document_income, decision = generate_paystub(applicant_id_str, income, identity, pdf_path)
    return applicant, decision, applicant_id_str, pdf_path


def _wipe_previous(db: Session) -> None:
    applicants = db.query(Applicant).filter(Applicant.hmda_source_id.like(f"{MARKER_PREFIX}:%")).all()
    for applicant in applicants:
        for case in db.query(Case).filter(Case.applicant_id == applicant.id).all():
            db.query(Discrepancy).filter(Discrepancy.case_id == case.id).delete()
            for doc in db.query(Document).filter(Document.case_id == case.id).all():
                db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).delete()
                db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == doc.id).delete()
            db.query(Document).filter(Document.case_id == case.id).delete()
        db.query(Case).filter(Case.applicant_id == applicant.id).delete()
        db.delete(applicant)
    db.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=150)
    parser.add_argument("--keep", action="store_true", help="Don't delete the fixture data afterward.")
    args = parser.parse_args()

    db = SessionLocal()
    _wipe_previous(db)

    injected_count = 0
    classifications = {"clean": 0, "minor": 0, "major": 0}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for i in range(args.count):
            applicant, decision, _applicant_id_str, pdf_path = _synthetic_applicant(i, tmp_dir)
            if decision.injected:
                injected_count += 1

            db.add(applicant)
            db.flush()
            case = Case(applicant_id=applicant.id, status=CaseStatus.SUBMITTED)
            db.add(case)
            db.flush()
            document = Document(
                case_id=case.id,
                doc_type=DocumentType.PAYSTUB,
                file_path=str(pdf_path),
                ocr_status=OcrStatus.PENDING_OCR,
            )
            db.add(document)
            db.commit()

            extract_document(db, document)
            discrepancies = run_verification(db, case)

            if not discrepancies:
                classifications["clean"] += 1
            elif any(d.severity == DiscrepancySeverity.MAJOR for d in discrepancies):
                classifications["major"] += 1
            else:
                classifications["minor"] += 1

            if (i + 1) % 25 == 0 or (i + 1) == args.count:
                print(f"Processed {i + 1}/{args.count}")

        if not args.keep:
            _wipe_previous(db)
        db.close()

    total = args.count
    print(f"\n{total} synthetic applicants processed.")
    print(f"Injector's ground truth: {injected_count}/{total} ({injected_count / total:.1%}) injected as discrepant.")
    print("\nPipeline's actual classification (OCR -> rules engine):")
    for label in ("clean", "minor", "major"):
        n = classifications[label]
        print(f"  {label:>5}: {n:4d} ({n / total:.1%})")

    discrepant_pct = (classifications["minor"] + classifications["major"]) / total
    print(
        f"\nTotal discrepant (minor + major): {discrepant_pct:.1%} (Phase 2 target band: 15-20% injected, ~80% clean)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
