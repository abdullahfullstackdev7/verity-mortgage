"""
Clean a raw HMDA Modified LAR export into a typed, deduplicated dataset used
to seed synthetic applicant documents in later phases.

Usage:
    python scripts/clean_hmda.py \
        --input data/raw/hmda/hmda_lar_2023_ca.csv \
        --output-dir data/processed \
        --sample-size 750

If --input is omitted, all `data/raw/hmda/hmda_lar_*.csv` files are
concatenated before cleaning.
"""

from __future__ import annotations

import argparse
import re
import sys
import uuid
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_HMDA_DIR = REPO_ROOT / "data" / "raw" / "hmda"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "processed"

# Stable, arbitrary namespace so applicant_id is deterministic across reruns
# of the same source row (same file + row index always yields the same id).
APPLICANT_ID_NAMESPACE = uuid.UUID("6f6a0b0e-6b1e-4e2c-9c3a-2d9a7e9e6b1a")

REQUIRED_COLUMNS = [
    "income",
    "loan_amount",
    "property_value",
    "debt_to_income_ratio",
    "action_taken",
]

# HMDA action_taken codes, mapped to a simplified ground-truth outcome label.
# 1 Loan originated, 2 Approved not accepted, 6 Purchased loan,
# 8 Preapproval approved not accepted -> approved
# 3 Denied, 7 Preapproval denied -> denied
# 4 Withdrawn, 5 Closed for incompleteness -> other
ACTION_TAKEN_MAP: dict[int, str] = {
    1: "approved",
    2: "approved",
    3: "denied",
    4: "other",
    5: "other",
    6: "approved",
    7: "denied",
    8: "approved",
}

_NULL_TOKENS = {"", "na", "n/a", "exempt", "nan", "none"}

_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


class CleanedApplicant(BaseModel):
    applicant_id: str
    hmda_source_id: str
    income: float
    loan_amount: float
    property_value: float
    debt_to_income_ratio: float
    outcome: str
    derived_loan_product_type: str | None = None
    loan_purpose: str | None = None
    occupancy_type: str | None = None


def _is_null_token(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().lower() in _NULL_TOKENS


def _parse_dti(value: object) -> float | None:
    """Normalize a DTI field (exact number or banded string) to a midpoint.

    Handles the Modified LAR conventions: a bare number ("36"), an
    open-ended band ("<20%", ">60%"), and a closed band ("30%-<36%",
    "36%-50%"). Bands are collapsed to their numeric midpoint; the two
    open-ended bands are padded by 5 points so they sit outside the
    adjacent closed band's range.
    """
    if _is_null_token(value):
        return None

    text = str(value).strip()

    if text.startswith("<"):
        nums = _NUM_RE.findall(text)
        return float(nums[0]) / 2 if nums else None
    if text.startswith(">"):
        nums = _NUM_RE.findall(text)
        return float(nums[0]) + 5.0 if nums else None
    if "-" in text:
        nums = _NUM_RE.findall(text)
        if len(nums) < 2:
            return None
        return (float(nums[0]) + float(nums[1])) / 2

    nums = _NUM_RE.findall(text)
    return float(nums[0]) if nums else None


def _parse_income_thousands(value: object) -> float | None:
    """HMDA reports income in thousands of dollars; convert to full dollars."""
    if _is_null_token(value):
        return None
    try:
        thousands = float(value)
    except ValueError:
        return None
    if thousands < 0:
        return None
    return thousands * 1000


def _parse_numeric(value: object) -> float | None:
    if _is_null_token(value):
        return None
    try:
        num = float(value)
    except ValueError:
        return None
    return num if num >= 0 else None


def load_raw_files(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        df = pd.read_csv(path, low_memory=False)
        df["_source_file"] = path.name
        frames.append(df)
    if not frames:
        raise FileNotFoundError(
            f"No raw HMDA files provided or found in {RAW_HMDA_DIR}"
        )
    return pd.concat(frames, ignore_index=True)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Type-cast, filter, and enrich a raw HMDA dataframe.

    Returns a dataframe matching the CleanedApplicant schema, with rows
    missing any required field dropped.
    """
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Input is missing required columns: {missing_cols}")

    out = pd.DataFrame(index=df.index)
    out["income"] = df["income"].map(_parse_income_thousands)
    out["loan_amount"] = df["loan_amount"].map(_parse_numeric)
    out["property_value"] = df["property_value"].map(_parse_numeric)
    out["debt_to_income_ratio"] = df["debt_to_income_ratio"].map(_parse_dti)

    action_taken = pd.to_numeric(df["action_taken"], errors="coerce")
    out["outcome"] = action_taken.map(ACTION_TAKEN_MAP)

    for col in ("derived_loan_product_type", "loan_purpose", "occupancy_type"):
        out[col] = df[col] if col in df.columns else None

    source_file = df["_source_file"] if "_source_file" in df.columns else "unknown"
    out["hmda_source_id"] = [
        f"{sf}:{idx}" for sf, idx in zip(source_file, df.index)
    ]
    out["applicant_id"] = [
        str(uuid.uuid5(APPLICANT_ID_NAMESPACE, source_id))
        for source_id in out["hmda_source_id"]
    ]

    required_after_parse = [
        "income",
        "loan_amount",
        "property_value",
        "debt_to_income_ratio",
        "outcome",
    ]
    before = len(out)
    out = out.dropna(subset=required_after_parse).reset_index(drop=True)
    dropped = before - len(out)
    if dropped:
        print(f"Dropped {dropped:,} of {before:,} rows with missing required fields")

    out = out.drop_duplicates(subset=["hmda_source_id"]).reset_index(drop=True)

    column_order = [
        "applicant_id",
        "hmda_source_id",
        "income",
        "loan_amount",
        "property_value",
        "debt_to_income_ratio",
        "outcome",
        "derived_loan_product_type",
        "loan_purpose",
        "occupancy_type",
    ]
    return out[column_order]


def validate_schema(df: pd.DataFrame, sample_size: int = 50) -> None:
    """Spot-check a sample of rows against the CleanedApplicant schema."""
    sample = df.sample(n=min(sample_size, len(df)), random_state=42) if len(df) else df
    errors: list[str] = []
    for row in sample.to_dict(orient="records"):
        try:
            CleanedApplicant(**row)
        except ValidationError as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError(f"Schema validation failed on {len(errors)} row(s): {errors[0]}")


def stratified_demo_sample(
    df: pd.DataFrame, sample_size: int, seed: int = 42
) -> pd.DataFrame:
    """Random stratified sample across outcome labels for the seeded demo."""
    if len(df) <= sample_size:
        return df.copy()

    frac = sample_size / len(df)
    parts = [
        group.sample(frac=frac, random_state=seed)
        for _, group in df.groupby("outcome")
    ]
    sampled = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0]
    return sampled.reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        nargs="*",
        default=None,
        help="Raw HMDA CSV file(s). Defaults to all files in data/raw/hmda/.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-size", type=int, default=750)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    input_paths = args.input or sorted(RAW_HMDA_DIR.glob("hmda_lar_*.csv"))
    if not input_paths:
        print(
            f"No input files given and none found in {RAW_HMDA_DIR}. "
            "See scripts/download_hmda.py for manual export instructions.",
            file=sys.stderr,
        )
        return 1

    raw_df = load_raw_files(input_paths)
    cleaned = clean(raw_df)
    validate_schema(cleaned)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    applicants_path = args.output_dir / "applicants.parquet"
    demo_path = args.output_dir / "applicants_sample_demo.parquet"

    cleaned.to_parquet(applicants_path, index=False)

    demo = stratified_demo_sample(cleaned, args.sample_size, seed=args.seed)
    demo.to_parquet(demo_path, index=False)

    print(f"Wrote {len(cleaned):,} rows to {applicants_path}")
    print(f"Wrote {len(demo):,} rows to {demo_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
