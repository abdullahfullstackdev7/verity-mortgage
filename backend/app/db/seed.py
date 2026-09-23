"""Seed the `applicants` table from the processed HMDA sample (Phase 1) so
the application has realistic applicants on first run.

    python -m backend.app.db.seed [--source demo|full]

Identity fields (name, address, employer) are generated the same way as the
Phase 2 document generators (`generators.identity.build_identity`), keyed by
applicant_id, so a seeded applicant's DB record matches the name/address/
employer printed on their generated documents.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.db.base import SessionLocal
from backend.app.db.models import Applicant
from generators.identity import build_identity

REPO_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"


def _load_applicants(source: str) -> pd.DataFrame:
    filename = "applicants_sample_demo.parquet" if source == "demo" else "applicants.parquet"
    path = PROCESSED_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run scripts/clean_hmda.py first (Phase 1).")
    return pd.read_parquet(path)


def seed_applicants(df: pd.DataFrame) -> int:
    session = SessionLocal()
    count = 0
    try:
        for row in df.to_dict(orient="records"):
            identity = build_identity(row["applicant_id"])
            values = {
                "id": uuid.UUID(row["applicant_id"]),
                "name": identity.full_name,
                "address": identity.address_line,
                "employer_name": identity.employer_name,
                "hmda_source_id": row["hmda_source_id"],
                "stated_income": row["income"],
                "stated_loan_amount": row["loan_amount"],
                "stated_property_value": row["property_value"],
                "stated_dti": row["debt_to_income_ratio"],
            }
            stmt = pg_insert(Applicant).values(**values)
            stmt = stmt.on_conflict_do_update(index_elements=[Applicant.id], set_=values)
            session.execute(stmt)
            count += 1
        session.commit()
    finally:
        session.close()
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["demo", "full"], default="demo")
    args = parser.parse_args()

    try:
        df = _load_applicants(args.source)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    count = seed_applicants(df)
    print(f"Seeded {count} applicants from the {args.source} sample.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
