from pathlib import Path

import pytest

from generators import discrepancy
from generators.bank_statement_generator import build_context as build_bank_context
from generators.identity import build_identity
from generators.paystub_generator import build_context as build_paystub_context
from generators.render import render_pdf
from generators.w2_generator import build_context as build_w2_context

APPLICANT_A = "5f4ab229-fc07-569a-a47b-49092c9d9cf9"
APPLICANT_B = "6b52e875-4b6d-543c-bf7c-df4dc9376c11"


class TestIdentity:
    def test_deterministic_across_calls(self):
        first = build_identity(APPLICANT_A)
        second = build_identity(APPLICANT_A)
        assert first == second

    def test_differs_across_applicants(self):
        a = build_identity(APPLICANT_A)
        b = build_identity(APPLICANT_B)
        assert a.full_name != b.full_name
        assert a.ssn_masked != b.ssn_masked

    def test_ssn_is_masked(self):
        identity = build_identity(APPLICANT_A)
        assert identity.ssn_masked.startswith("XXX-XX-")
        assert len(identity.ssn_masked.split("-")[-1]) == 4


class TestDiscrepancyDecision:
    def test_deterministic_across_calls(self):
        first = discrepancy.decide(APPLICANT_A)
        second = discrepancy.decide(APPLICANT_A)
        assert first == second

    def test_injection_rate_within_target_band(self):
        applicant_ids = [f"synthetic-applicant-{i}" for i in range(4000)]
        injected = sum(1 for aid in applicant_ids if discrepancy.decide(aid).injected)
        rate = injected / len(applicant_ids)
        # Target band is 15-20%; allow slack for hash-based sampling variance.
        assert 0.12 <= rate <= 0.23

    def test_variance_within_declared_range_when_injected(self):
        applicant_ids = [f"synthetic-applicant-{i}" for i in range(2000)]
        for aid in applicant_ids:
            decision = discrepancy.decide(aid)
            if decision.injected:
                assert discrepancy.MIN_VARIANCE_PCT <= decision.variance_pct <= discrepancy.MAX_VARIANCE_PCT
                assert decision.direction in ("above", "below")

    def test_apply_income_discrepancy_matches_direction(self):
        # Find an applicant with an injected discrepancy deterministically.
        aid = next(
            a
            for a in (f"synthetic-applicant-{i}" for i in range(200))
            if discrepancy.decide(a).injected
        )
        stated_income = 90_000.0
        document_income, decision = discrepancy.apply_income_discrepancy(stated_income, aid)
        assert decision.injected
        if decision.direction == "above":
            assert document_income > stated_income
        else:
            assert document_income < stated_income

    def test_apply_income_discrepancy_no_injection_returns_stated_value(self):
        aid = next(
            a
            for a in (f"synthetic-applicant-{i}" for i in range(200))
            if not discrepancy.decide(a).injected
        )
        stated_income = 90_000.0
        document_income, decision = discrepancy.apply_income_discrepancy(stated_income, aid)
        assert not decision.injected
        assert document_income == stated_income


class TestPaystubContext:
    def test_net_pay_equals_gross_minus_deductions(self):
        identity = build_identity(APPLICANT_A)
        context, _document_income, _decision = build_paystub_context(
            APPLICANT_A, 90_000.0, identity
        )
        expected_net = round(
            context["gross_pay"]
            - context["federal_tax"]
            - context["state_tax"]
            - context["social_security"]
            - context["medicare"],
            2,
        )
        assert context["net_pay"] == expected_net

    def test_gross_pay_times_periods_matches_document_income(self):
        identity = build_identity(APPLICANT_A)
        context, document_income, _decision = build_paystub_context(
            APPLICANT_A, 90_000.0, identity
        )
        assert round(context["gross_pay"] * 26, 2) == pytest.approx(document_income, abs=0.5)


class TestBankStatementContext:
    def test_ending_balance_matches_transaction_ledger(self):
        identity = build_identity(APPLICANT_A)
        context = build_bank_context(APPLICANT_A, 90_000.0, identity)
        running = context["beginning_balance"]
        for txn in context["transactions"]:
            running = round(running + txn["amount"], 2)
            assert running == txn["balance"]
        assert running == context["ending_balance"]

    def test_deposits_and_withdrawals_sum_correctly(self):
        identity = build_identity(APPLICANT_A)
        context = build_bank_context(APPLICANT_A, 90_000.0, identity)
        net = context["beginning_balance"] + context["total_deposits"] - context["total_withdrawals"]
        assert round(net, 2) == context["ending_balance"]


class TestW2Context:
    def test_box1_matches_stated_income(self):
        identity = build_identity(APPLICANT_A)
        context = build_w2_context(90_000.0, identity)
        assert context["box1_wages"] == 90_000.0
        assert context["box3_ss_wages"] == 90_000.0
        assert context["box5_medicare_wages"] == 90_000.0


class TestRenderPdf:
    def test_renders_nonempty_pdf(self, tmp_path: Path):
        identity = build_identity(APPLICANT_A)
        context, _income, _decision = build_paystub_context(APPLICANT_A, 90_000.0, identity)
        output_path = tmp_path / "paystub.pdf"
        render_pdf("paystub_template.html", context, output_path)
        assert output_path.exists()
        assert output_path.read_bytes().startswith(b"%PDF")
