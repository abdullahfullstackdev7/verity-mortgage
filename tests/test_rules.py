from __future__ import annotations

import uuid

from backend.app.db.models.enums import DiscrepancySeverity
from backend.app.services.rules.rules import (
    annualization_factor,
    check_bank_deposit,
    check_dti,
    check_employer_name,
    check_income,
)

DOC_ID = uuid.uuid4()


class TestAnnualizationFactor:
    def test_known_frequencies(self):
        assert annualization_factor("Biweekly") == 26
        assert annualization_factor("weekly") == 52
        assert annualization_factor("Monthly") == 12
        assert annualization_factor("SemiMonthly") == 24

    def test_unknown_or_missing_defaults_to_biweekly(self):
        assert annualization_factor(None) == 26
        assert annualization_factor("quarterly") == 26


class TestCheckIncome:
    def test_within_tolerance_is_clean(self):
        # 5% below stated is within the 10% clean band.
        result = check_income(100_000, 95_000, "income_paystub", DOC_ID)
        assert result is None

    def test_minor_variance(self):
        # 15% below stated: outside 10% clean, inside 20% major cutoff.
        result = check_income(100_000, 85_000, "income_paystub", DOC_ID)
        assert result is not None
        assert result.severity == DiscrepancySeverity.MINOR
        assert result.field_name == "income_paystub"
        assert result.variance_pct == 15.0
        assert result.source_document_id == DOC_ID

    def test_major_variance(self):
        # 30% below stated: beyond the 20% major cutoff.
        result = check_income(100_000, 70_000, "income_paystub", DOC_ID)
        assert result is not None
        assert result.severity == DiscrepancySeverity.MAJOR
        assert result.variance_pct == 30.0

    def test_variance_above_stated_also_flagged(self):
        result = check_income(100_000, 130_000, "income_w2", DOC_ID)
        assert result is not None
        assert result.severity == DiscrepancySeverity.MAJOR

    def test_zero_stated_income_is_not_evaluated(self):
        assert check_income(0, 50_000, "income_paystub", DOC_ID) is None


class TestCheckEmployerName:
    IDENTICAL_A = [1.0, 0.0, 0.0]
    IDENTICAL_B = [1.0, 0.0, 0.0]
    SIMILAR = [0.75, 0.6614, 0.0]  # cosine similarity ~0.75 with IDENTICAL_A (between the 0.60/0.85 bands)
    DISSIMILAR = [0.0, 1.0, 0.0]  # orthogonal -> similarity 0.0

    def test_matching_embeddings_is_clean(self):
        result = check_employer_name(
            "Acme Corp", "Acme Corp", self.IDENTICAL_A, self.IDENTICAL_B,
            "employer_name_paystub", DOC_ID,
        )
        assert result is None

    def test_moderately_similar_is_minor(self):
        result = check_employer_name(
            "Acme Corp", "Acme Corporation", self.IDENTICAL_A, self.SIMILAR,
            "employer_name_paystub", DOC_ID,
        )
        assert result is not None
        assert result.severity == DiscrepancySeverity.MINOR

    def test_dissimilar_is_major(self):
        result = check_employer_name(
            "Acme Corp", "Totally Different Co", self.IDENTICAL_A, self.DISSIMILAR,
            "employer_name_w2", DOC_ID,
        )
        assert result is not None
        assert result.severity == DiscrepancySeverity.MAJOR
        assert result.stated_value == "Acme Corp"
        assert result.document_value == "Totally Different Co"

    def test_missing_extracted_name_returns_none(self):
        assert check_employer_name("Acme", "", [1.0], [1.0], "employer_name_paystub", DOC_ID) is None


class TestCheckBankDeposit:
    def test_within_tolerance_is_clean(self):
        # ~10% below expected net deposit for a 30-day period: within the
        # 15% clean band.
        stated_income = 100_000
        expected = stated_income * (1 - 0.2365) * (30 / 365)
        result = check_bank_deposit(stated_income, expected * 0.92, DOC_ID)
        assert result is None

    def test_minor_variance(self):
        stated_income = 100_000
        expected = stated_income * (1 - 0.2365) * (30 / 365)
        result = check_bank_deposit(stated_income, expected * 0.75, DOC_ID)
        assert result is not None
        assert result.severity == DiscrepancySeverity.MINOR
        assert result.field_name == "bank_deposit_total"

    def test_major_variance(self):
        stated_income = 100_000
        expected = stated_income * (1 - 0.2365) * (30 / 365)
        result = check_bank_deposit(stated_income, expected * 0.4, DOC_ID)
        assert result is not None
        assert result.severity == DiscrepancySeverity.MAJOR

    def test_zero_stated_income_is_not_evaluated(self):
        assert check_bank_deposit(0, 5000, DOC_ID) is None


class TestCheckDti:
    def test_matching_income_reproduces_stated_dti_and_is_clean(self):
        # When extracted income equals stated income, the recomputed DTI
        # must equal the stated DTI exactly.
        result = check_dti(100_000, 36.0, 100_000, DOC_ID)
        assert result is None

    def test_lower_extracted_income_raises_dti_to_minor(self):
        # Extracted income notably below stated pushes the recomputed DTI
        # up (worse) relative to stated.
        result = check_dti(100_000, 36.0, 88_000, DOC_ID)
        assert result is not None
        assert result.severity == DiscrepancySeverity.MINOR
        assert float(result.document_value) > 36.0

    def test_much_lower_extracted_income_is_major(self):
        result = check_dti(100_000, 36.0, 60_000, DOC_ID)
        assert result is not None
        assert result.severity == DiscrepancySeverity.MAJOR

    def test_zero_extracted_income_is_not_evaluated(self):
        assert check_dti(100_000, 36.0, 0, DOC_ID) is None
