"""
Instructions and loader for the HMDA Modified LAR dataset.

The FFIEC HMDA Platform does not offer a stable, unauthenticated API for bulk
CSV export, so this script does not perform an automated download. Instead it
documents the manual export steps and provides a `load_raw` helper plus a CLI
that validates a manually-downloaded file is present and well-formed before
`clean_hmda.py` processes it.

Manual export steps
--------------------
1. Go to the HMDA Data Browser: https://ffiec.cfpb.gov/data-browser/
2. Filter by the most recent full filing year and by one or two states, to
   keep the export a manageable size for a demo (a national file can run
   into millions of rows).
3. Use "Create export" / "Download data" and export as CSV.
4. Confirm the export includes at minimum: `income`, `loan_amount`,
   `property_value`, `debt_to_income_ratio`, `action_taken`,
   `derived_loan_product_type`, `loan_purpose`, `occupancy_type`.
5. Save the file, unmodified, into `data/raw/hmda/` using the naming
   convention `hmda_lar_<year>_<state>.csv` (e.g. `hmda_lar_2023_ca.csv`).
   Keep this file read-only after download; all cleaning happens in
   `clean_hmda.py` and writes only to `data/processed/`.

Reference: CFPB "Beginner's Guide to Accessing and Using HMDA Data" for
field definitions, and https://ffiec.cfpb.gov/data-publication/modified-lar
for the Modified LAR publication page.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_HMDA_DIR = REPO_ROOT / "data" / "raw" / "hmda"

REQUIRED_COLUMNS = [
    "income",
    "loan_amount",
    "property_value",
    "debt_to_income_ratio",
    "action_taken",
    "derived_loan_product_type",
    "loan_purpose",
    "occupancy_type",
]


def load_raw(path: Path) -> pd.DataFrame:
    """Load a manually-exported HMDA CSV without mutating it."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Follow the manual export steps in this "
            f"module's docstring and place the CSV in {RAW_HMDA_DIR}."
        )
    return pd.read_csv(path, low_memory=False)


def validate_columns(df: pd.DataFrame) -> list[str]:
    """Return the list of required columns that are missing, if any."""
    return [col for col in REQUIRED_COLUMNS if col not in df.columns]


def find_raw_files() -> list[Path]:
    if not RAW_HMDA_DIR.exists():
        return []
    return sorted(RAW_HMDA_DIR.glob("hmda_lar_*.csv"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a manually-downloaded HMDA Modified LAR export. "
            "See this module's docstring for the manual download steps."
        )
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help=(
            "Path to a specific raw CSV to validate. Defaults to scanning "
            f"{RAW_HMDA_DIR} for files named hmda_lar_<year>_<state>.csv"
        ),
    )
    args = parser.parse_args()

    candidates = [args.file] if args.file else find_raw_files()

    if not candidates:
        print(__doc__)
        print(f"\nNo raw HMDA files found in {RAW_HMDA_DIR}.", file=sys.stderr)
        return 1

    exit_code = 0
    for path in candidates:
        try:
            df = load_raw(path)
        except FileNotFoundError as exc:
            print(f"[FAIL] {path}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        missing = validate_columns(df)
        if missing:
            print(
                f"[FAIL] {path}: missing required columns: {missing}",
                file=sys.stderr,
            )
            exit_code = 1
        else:
            print(f"[OK]   {path}: {len(df):,} rows, all required columns present")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
