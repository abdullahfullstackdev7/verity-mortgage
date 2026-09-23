"""Document generation CLI.

    python -m generators.build_all --count 1000

Reads the processed HMDA applicant sample, and for each applicant renders a
pay stub, bank statement, and W-2 PDF into
`data/documents/generated/<applicant_id>/`. Roughly 15-20% of applicants get
a deliberately mismatched pay-stub income figure (see `discrepancy.py`); the
ground truth for those injected mismatches is written to
`data/processed/discrepancy_ground_truth.parquet` so the extraction and
verification pipeline built in later phases can be scored against it.

A configurable fraction of applicants additionally get scan-degraded JPEG
copies of their documents written to `data/documents/degraded/<applicant_id>/`
for OCR robustness testing.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

from generators import bank_statement_generator, degrade, w2_generator
from generators.identity import build_identity
from generators.paystub_generator import generate as generate_paystub

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
GENERATED_DIR = REPO_ROOT / "data" / "documents" / "generated"
DEGRADED_DIR = REPO_ROOT / "data" / "documents" / "degraded"

DOC_TYPES = ["paystub", "bank_statement", "w2"]


def _load_applicants(source: str, count: int | None) -> pd.DataFrame:
    filename = "applicants_sample_demo.parquet" if source == "demo" else "applicants.parquet"
    path = PROCESSED_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run scripts/clean_hmda.py first (Phase 1)."
        )
    df = pd.read_parquet(path)
    if count is not None:
        df = df.head(count)
    return df.reset_index(drop=True)


def _should_degrade(applicant_id: str, fraction: float) -> bool:
    if fraction <= 0:
        return False
    digest = hashlib.sha256(f"degrade-select:{applicant_id}".encode()).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return bucket < fraction


def build_for_applicant(row: pd.Series, degrade_fraction: float) -> list[dict]:
    applicant_id = row["applicant_id"]
    stated_income = float(row["income"])

    identity = build_identity(applicant_id)
    out_dir = GENERATED_DIR / applicant_id

    paystub_path = out_dir / "paystub.pdf"
    bank_statement_path = out_dir / "bank_statement.pdf"
    w2_path = out_dir / "w2.pdf"

    document_income, decision = generate_paystub(
        applicant_id, stated_income, identity, paystub_path
    )
    bank_statement_generator.generate(applicant_id, stated_income, identity, bank_statement_path)
    w2_generator.generate(stated_income, identity, w2_path)

    ground_truth_rows: list[dict] = []
    if decision.injected:
        ground_truth_rows.append(
            {
                "applicant_id": applicant_id,
                "document_type": "paystub",
                "field_name": "annualized_income",
                "stated_value": stated_income,
                "document_value": document_income,
                "direction": decision.direction,
                "variance_pct": decision.variance_pct,
            }
        )

    if _should_degrade(applicant_id, degrade_fraction):
        doc_paths = {
            "paystub": paystub_path,
            "bank_statement": bank_statement_path,
            "w2": w2_path,
        }
        for doc_type, pdf_path in doc_paths.items():
            output_path = DEGRADED_DIR / applicant_id / f"{doc_type}.jpg"
            degrade.degrade_pdf(pdf_path, output_path, applicant_id, doc_type)

    return ground_truth_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=["demo", "full"],
        default="demo",
        help="Which processed dataset to draw applicants from (default: demo sample).",
    )
    parser.add_argument(
        "--count", type=int, default=None, help="Limit to the first N applicants."
    )
    parser.add_argument(
        "--degrade-fraction",
        type=float,
        default=0.2,
        help="Fraction of applicants that also get scan-degraded JPEG copies (default 0.2).",
    )
    args = parser.parse_args()

    try:
        applicants = _load_applicants(args.source, args.count)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    DEGRADED_DIR.mkdir(parents=True, exist_ok=True)

    all_ground_truth: list[dict] = []
    total = len(applicants)
    for i, row in applicants.iterrows():
        all_ground_truth.extend(build_for_applicant(row, args.degrade_fraction))
        if (i + 1) % 50 == 0 or (i + 1) == total:
            print(f"Generated documents for {i + 1}/{total} applicants")

    ground_truth_df = pd.DataFrame(
        all_ground_truth,
        columns=[
            "applicant_id",
            "document_type",
            "field_name",
            "stated_value",
            "document_value",
            "direction",
            "variance_pct",
        ],
    )
    ground_truth_path = PROCESSED_DIR / "discrepancy_ground_truth.parquet"
    ground_truth_df.to_parquet(ground_truth_path, index=False)

    print(
        f"\nDone. {total} applicants processed, "
        f"{len(ground_truth_df)} with an injected discrepancy "
        f"({len(ground_truth_df) / total:.1%})."
    )
    print(f"Ground truth written to {ground_truth_path}")
    print(f"Documents written to {GENERATED_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
