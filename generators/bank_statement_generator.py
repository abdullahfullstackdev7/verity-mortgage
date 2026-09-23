"""Generate a synthetic one-month bank statement PDF for one applicant.

Deposits are built from the applicant's stated HMDA income (not the
possibly-discrepant pay stub figure), so the bank statement acts as a clean
cross-check source for later verification phases. A handful of everyday
debit transactions are added around the payroll deposits for realism.
"""

from __future__ import annotations

import datetime as dt
import random
from pathlib import Path

from faker import Faker

from generators.identity import Identity
from generators.render import render_pdf

TEMPLATE_NAME = "bank_statement_template.html"
ANCHOR_YEAR = 2024

FEDERAL_TAX_RATE = 0.12
STATE_TAX_RATE = 0.04
SOCIAL_SECURITY_RATE = 0.062
MEDICARE_RATE = 0.0145

_DEBIT_CATEGORIES = [
    ("Rent Payment", 900, 2200),
    ("Grocery Store", 40, 180),
    ("Electric Utility", 60, 180),
    ("Mobile Phone Bill", 40, 90),
    ("Auto Insurance", 90, 220),
    ("Streaming Subscription", 8, 20),
    ("Restaurant", 15, 90),
]


def _rng_for(applicant_id: str) -> random.Random:
    return random.Random(int.from_bytes(applicant_id.encode()[:8], "little", signed=False))


def _statement_month(applicant_id: str) -> int:
    rng = _rng_for(applicant_id)
    return rng.randint(1, 11)  # leave room for a full month within ANCHOR_YEAR


def build_context(applicant_id: str, stated_income: float, identity: Identity) -> dict:
    rng = _rng_for(applicant_id)
    fake = Faker()
    fake.seed_instance(int.from_bytes(applicant_id.encode()[:8], "little", signed=False))

    month = _statement_month(applicant_id)
    period_start = dt.date(ANCHOR_YEAR, month, 1)
    next_month = period_start.replace(day=28) + dt.timedelta(days=4)
    period_end = next_month - dt.timedelta(days=next_month.day)

    biweekly_gross = stated_income / 26
    biweekly_net = biweekly_gross * (
        1 - FEDERAL_TAX_RATE - STATE_TAX_RATE - SOCIAL_SECURITY_RATE - MEDICARE_RATE
    )

    beginning_balance = round(rng.uniform(1500, 9000), 2)
    balance = beginning_balance
    transactions = []

    deposit_days = sorted(rng.sample(range(2, period_end.day - 1), k=2))
    debit_days = sorted(
        rng.sample(
            [d for d in range(1, period_end.day + 1) if d not in deposit_days],
            k=min(len(_DEBIT_CATEGORIES), period_end.day - 2),
        )
    )

    events: list[tuple[int, str, float]] = []
    for day in deposit_days:
        events.append((day, "Payroll Direct Deposit", round(biweekly_net, 2)))
    for day, (label, low, high) in zip(debit_days, rng.sample(_DEBIT_CATEGORIES, k=len(debit_days))):
        amount = -round(rng.uniform(low, high), 2)
        events.append((day, label, amount))

    events.sort(key=lambda e: e[0])

    total_deposits = 0.0
    total_withdrawals = 0.0
    for day, description, amount in events:
        balance = round(balance + amount, 2)
        if amount >= 0:
            total_deposits += amount
        else:
            total_withdrawals += -amount
        transactions.append(
            {
                "date": dt.date(ANCHOR_YEAR, month, day).isoformat(),
                "description": description,
                "amount": amount,
                "balance": balance,
            }
        )

    context = {
        "bank_name": identity.bank_name,
        "statement_period_start": period_start.isoformat(),
        "statement_period_end": period_end.isoformat(),
        "account_holder_name": identity.full_name,
        "account_holder_address": identity.address_line,
        "account_number_masked": identity.account_number_masked,
        "beginning_balance": beginning_balance,
        "ending_balance": balance,
        "total_deposits": round(total_deposits, 2),
        "total_withdrawals": round(total_withdrawals, 2),
        "transactions": transactions,
    }
    return context


def generate(
    applicant_id: str,
    stated_income: float,
    identity: Identity,
    output_path: Path,
) -> None:
    context = build_context(applicant_id, stated_income, identity)
    render_pdf(TEMPLATE_NAME, context, output_path)
