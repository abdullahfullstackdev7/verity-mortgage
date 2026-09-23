"""Deterministic regex + layout-anchor field parsers, one per document type.

These parse the row-reconstructed OCR text from `ocr.py`. Because the
documents are generated from our own fixed templates (Phase 2), a small set
of layout anchors (a known label row, a known column split, a known unique
label string) reliably locates each field without a general-purpose table
parser. No LLM calls happen here; the LLM fallback (`llm_fallback.py`) only
kicks in afterward for fields this module couldn't find or found with low
confidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from backend.app.db.models.enums import DocumentType
from backend.app.services.extraction.ocr import OcrPage, Token, group_rows, row_text

MONEY_RE = re.compile(r"[\$Ss]?\s*(\d[\d,]*\.\d{2})")


@dataclass(frozen=True)
class ExtractedValue:
    value: str
    confidence: float
    raw_text: str


def find_money_values(text: str) -> list[float]:
    return [float(m.group(1).replace(",", "")) for m in MONEY_RE.finditer(text)]


def find_row_index(rows: list[list[Token]], predicate: Callable[[list[Token]], bool]) -> int | None:
    for i, row in enumerate(rows):
        if predicate(row):
            return i
    return None


def split_left_right(row: list[Token], page_width: float) -> tuple[list[Token], list[Token]]:
    midpoint = page_width / 2
    left = [t for t in row if t.x_center < midpoint]
    right = [t for t in row if t.x_center >= midpoint]
    return left, right


def tokens_text(tokens: list[Token]) -> str:
    return " ".join(t.text for t in tokens)


def tokens_confidence(tokens: list[Token]) -> float:
    if not tokens:
        return 0.0
    return sum(t.confidence for t in tokens) / len(tokens)


def _has_both(row: list[Token], word_a: str, word_b: str) -> bool:
    text = row_text(row).lower()
    return word_a in text and word_b in text


def parse_paystub(page: OcrPage) -> dict[str, ExtractedValue]:
    rows = group_rows(page)
    result: dict[str, ExtractedValue] = {}

    header_idx = find_row_index(rows, lambda r: _has_both(r, "employer", "employee"))
    if header_idx is not None and header_idx + 1 < len(rows):
        value_row = rows[header_idx + 1]
        left, _right = split_left_right(value_row, page.width)
        if left:
            result["employer_name"] = ExtractedValue(
                tokens_text(left), tokens_confidence(left), row_text(value_row)
            )

    gross_idx = find_row_index(rows, lambda r: "gross" in row_text(r).lower())
    if gross_idx is not None:
        text = row_text(rows[gross_idx])
        amounts = find_money_values(text)
        confidence = tokens_confidence(rows[gross_idx])
        if amounts:
            result["gross_pay_current"] = ExtractedValue(f"{amounts[0]:.2f}", confidence, text)
        freq_match = re.search(r"\(([A-Za-z]+)\)", text)
        if freq_match:
            result["pay_frequency"] = ExtractedValue(freq_match.group(1), confidence, text)

    return result


def parse_bank_statement(page: OcrPage) -> dict[str, ExtractedValue]:
    rows = group_rows(page)
    result: dict[str, ExtractedValue] = {}

    # The summary row (beginning balance, total deposits, total withdrawals,
    # ending balance) is the only row with exactly four money-shaped tokens.
    summary_idx = find_row_index(rows, lambda r: len(find_money_values(row_text(r))) == 4)
    if summary_idx is not None:
        text = row_text(rows[summary_idx])
        amounts = find_money_values(text)
        confidence = tokens_confidence(rows[summary_idx])
        for label, amount in zip(
            ["beginning_balance", "total_deposits", "total_withdrawals", "ending_balance"], amounts
        ):
            result[label] = ExtractedValue(f"{amount:.2f}", confidence, text)

    payroll_total = 0.0
    payroll_confidences: list[float] = []
    for row in rows:
        text = row_text(row)
        if "payroll" in text.lower():
            amounts = find_money_values(text)
            if amounts:
                payroll_total += amounts[0]
                payroll_confidences.append(tokens_confidence(row))

    if payroll_confidences:
        result["payroll_deposit_total"] = ExtractedValue(
            f"{payroll_total:.2f}",
            sum(payroll_confidences) / len(payroll_confidences),
            "aggregated from rows matching 'Payroll'",
        )

    return result


def parse_w2(page: OcrPage) -> dict[str, ExtractedValue]:
    rows = group_rows(page)
    result: dict[str, ExtractedValue] = {}

    header_idx = find_row_index(rows, lambda r: _has_both(r, "employer", "employee"))
    if header_idx is not None and header_idx + 1 < len(rows):
        value_row = rows[header_idx + 1]
        left, _right = split_left_right(value_row, page.width)
        if left:
            result["employer_name"] = ExtractedValue(
                tokens_text(left), tokens_confidence(left), row_text(value_row)
            )

    ein_pattern = re.compile(r"EIN:?\s*([\d\-]+)", re.IGNORECASE)
    ein_idx = find_row_index(rows, lambda r: ein_pattern.search(row_text(r)) is not None)
    if ein_idx is not None:
        text = row_text(rows[ein_idx])
        match = ein_pattern.search(text)
        if match:
            result["employer_ein"] = ExtractedValue(
                match.group(1), tokens_confidence(rows[ein_idx]), text
            )

    box1_idx = find_row_index(
        rows, lambda r: "wages, tips, other compensation" in row_text(r).lower()
    )
    if box1_idx is not None:
        text = row_text(rows[box1_idx])
        amounts = find_money_values(text)
        if amounts:
            result["box1_wages"] = ExtractedValue(
                f"{amounts[0]:.2f}", tokens_confidence(rows[box1_idx]), text
            )

    return result


PARSERS: dict[DocumentType, Callable[[OcrPage], dict[str, ExtractedValue]]] = {
    DocumentType.PAYSTUB: parse_paystub,
    DocumentType.BANK_STATEMENT: parse_bank_statement,
    DocumentType.W2: parse_w2,
}

REQUIRED_FIELDS: dict[DocumentType, set[str]] = {
    DocumentType.PAYSTUB: {"employer_name", "gross_pay_current"},
    DocumentType.BANK_STATEMENT: {"beginning_balance", "ending_balance", "payroll_deposit_total"},
    DocumentType.W2: {"employer_name", "employer_ein", "box1_wages"},
}

FIELD_CONFIDENCE_THRESHOLD = 0.6
