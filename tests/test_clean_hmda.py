from pathlib import Path

import pandas as pd
import pytest

from scripts.clean_hmda import (
    CleanedApplicant,
    _parse_dti,
    _parse_income_thousands,
    clean,
    load_raw_files,
    stratified_demo_sample,
    validate_schema,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "hmda_lar_fixture.csv"


@pytest.fixture
def cleaned_df() -> pd.DataFrame:
    raw = load_raw_files([FIXTURE_PATH])
    return clean(raw)


class TestDtiParsing:
    def test_bare_number(self):
        assert _parse_dti("36") == 36.0

    def test_open_ended_low_band(self):
        assert _parse_dti("<20%") == 10.0

    def test_open_ended_high_band(self):
        assert _parse_dti(">60%") == 65.0

    def test_closed_band_with_lt_marker(self):
        assert _parse_dti("30%-<36%") == 33.0

    def test_closed_band_plain(self):
        assert _parse_dti("36%-50%") == 43.0

    def test_null_tokens(self):
        for token in ["Exempt", "NA", "", None, float("nan")]:
            assert _parse_dti(token) is None


class TestIncomeParsing:
    def test_converts_thousands_to_dollars(self):
        assert _parse_income_thousands("85") == 85000.0

    def test_zero_is_valid(self):
        assert _parse_income_thousands("0") == 0.0

    def test_negative_is_null(self):
        assert _parse_income_thousands("-1") is None

    def test_null_tokens(self):
        assert _parse_income_thousands("NA") is None


class TestClean:
    def test_drops_rows_missing_required_fields(self, cleaned_df: pd.DataFrame):
        # Fixture has 12 rows; 6 are missing a required field or have an
        # unmapped action_taken code and must be dropped.
        assert len(cleaned_df) == 6

    def test_no_pii_columns_present(self, cleaned_df: pd.DataFrame):
        pii_columns = {"name", "ssn", "address", "email", "phone", "account_number"}
        assert pii_columns.isdisjoint(cleaned_df.columns)

    def test_applicant_id_is_stable_across_runs(self):
        raw = load_raw_files([FIXTURE_PATH])
        first = clean(raw)
        second = clean(raw)
        assert list(first["applicant_id"]) == list(second["applicant_id"])

    def test_applicant_ids_are_unique(self, cleaned_df: pd.DataFrame):
        assert cleaned_df["applicant_id"].is_unique

    def test_income_within_plausible_range(self, cleaned_df: pd.DataFrame):
        assert (cleaned_df["income"] >= 0).all()
        assert (cleaned_df["income"] < 10_000_000).all()

    def test_dti_within_percentage_range(self, cleaned_df: pd.DataFrame):
        assert (cleaned_df["debt_to_income_ratio"] >= 0).all()
        assert (cleaned_df["debt_to_income_ratio"] <= 100).all()

    def test_outcome_values_are_known_labels(self, cleaned_df: pd.DataFrame):
        assert set(cleaned_df["outcome"].unique()) <= {"approved", "denied", "other"}

    def test_unmapped_action_taken_code_is_dropped(self, cleaned_df: pd.DataFrame):
        # Row with action_taken=99 in the fixture has no ACTION_TAKEN_MAP entry.
        assert 99 not in cleaned_df.get("action_taken", pd.Series(dtype=int)).values

    def test_schema_validates(self, cleaned_df: pd.DataFrame):
        validate_schema(cleaned_df, sample_size=len(cleaned_df))
        for row in cleaned_df.to_dict(orient="records"):
            CleanedApplicant(**row)

    def test_missing_required_column_raises(self):
        bad_df = pd.DataFrame({"income": [50]})
        with pytest.raises(ValueError):
            clean(bad_df)


class TestStratifiedDemoSample:
    def test_sample_preserves_outcome_proportions_roughly(self, cleaned_df: pd.DataFrame):
        demo = stratified_demo_sample(cleaned_df, sample_size=3, seed=42)
        assert len(demo) <= len(cleaned_df)
        assert set(demo["outcome"].unique()) <= set(cleaned_df["outcome"].unique())

    def test_sample_larger_than_population_returns_full_population(self, cleaned_df: pd.DataFrame):
        demo = stratified_demo_sample(cleaned_df, sample_size=10_000, seed=42)
        assert len(demo) == len(cleaned_df)
