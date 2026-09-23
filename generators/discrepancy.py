"""Deterministic discrepancy injection for a minority of generated applicants.

For roughly 15-20% of applicants, the pay stub's annualized income figure is
deliberately set 15-30% above or below the applicant's stated HMDA income.
The decision (whether to inject, in which direction, and by how much) is
derived entirely from a hash of the applicant_id, so re-running document
generation always reproduces the same injected discrepancies.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

INJECTION_RATE = 0.175  # midpoint of the 15-20% target band
MIN_VARIANCE_PCT = 15.0
MAX_VARIANCE_PCT = 30.0


@dataclass(frozen=True)
class DiscrepancyDecision:
    injected: bool
    direction: str | None  # "above" or "below"
    variance_pct: float | None


def _rng_for(applicant_id: str) -> random.Random:
    seed = int(hashlib.sha256(f"discrepancy:{applicant_id}".encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def decide(applicant_id: str) -> DiscrepancyDecision:
    rng = _rng_for(applicant_id)
    injected = rng.random() < INJECTION_RATE
    if not injected:
        return DiscrepancyDecision(injected=False, direction=None, variance_pct=None)

    direction = rng.choice(["above", "below"])
    variance_pct = round(rng.uniform(MIN_VARIANCE_PCT, MAX_VARIANCE_PCT), 2)
    return DiscrepancyDecision(injected=True, direction=direction, variance_pct=variance_pct)


def apply_income_discrepancy(stated_income: float, applicant_id: str) -> tuple[float, DiscrepancyDecision]:
    """Return the (possibly altered) annualized income to print on the pay
    stub, along with the decision that produced it."""
    decision = decide(applicant_id)
    if not decision.injected:
        return stated_income, decision

    assert decision.variance_pct is not None  # guaranteed by decide() when injected=True
    factor = 1 + decision.variance_pct / 100 if decision.direction == "above" else 1 - decision.variance_pct / 100
    document_income = round(stated_income * factor, 2)
    return document_income, decision
