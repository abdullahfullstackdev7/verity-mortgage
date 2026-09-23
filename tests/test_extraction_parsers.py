from __future__ import annotations

from backend.app.services.extraction.ocr import OcrPage, Token
from backend.app.services.extraction.parsers import (
    find_money_values,
    parse_bank_statement,
    parse_paystub,
    parse_w2,
)

PAGE_WIDTH = 1200
PAGE_HEIGHT = 2000


def make_token(text: str, confidence: float, x: float, y: float, width: float = 60, height: float = 20) -> Token:
    return Token(text=text, confidence=confidence, x_min=x, x_max=x + width, y_min=y, y_max=y + height)


def make_page(rows: list[list[Token]]) -> OcrPage:
    tokens = [t for row in rows for t in row]
    return OcrPage(tokens=tokens, width=PAGE_WIDTH, height=PAGE_HEIGHT)


class TestFindMoneyValues:
    def test_plain_dollar_sign(self):
        assert find_money_values("Total: $1,234.56") == [1234.56]

    def test_ocr_misread_s_for_dollar(self):
        assert find_money_values("Balance S9956.55") == [9956.55]

    def test_no_amount_returns_empty(self):
        assert find_money_values("no numbers here") == []

    def test_multiple_amounts_in_order(self):
        assert find_money_values("S100.00 200.50 $3.25") == [100.00, 200.50, 3.25]


class TestParsePaystub:
    def test_extracts_employer_name_gross_pay_and_frequency(self):
        page = make_page(
            [
                [make_token("Employer", 1.0, 100, 100), make_token("Employee", 1.0, 800, 100)],
                [
                    make_token("Acme", 0.95, 100, 200),
                    make_token("Corp", 0.90, 180, 200),
                    make_token("John", 0.99, 800, 200),
                    make_token("Doe", 0.98, 880, 200),
                ],
                [
                    make_token("Gross", 0.9, 100, 300),
                    make_token("Pay", 0.9, 170, 300),
                    make_token("(Biweekly)", 0.8, 230, 300),
                    make_token("3846.25", 0.85, 500, 300),
                    make_token("S46155.00", 0.7, 700, 300),
                ],
            ]
        )
        result = parse_paystub(page)
        assert result["employer_name"].value == "Acme Corp"
        assert result["gross_pay_current"].value == "3846.25"
        assert result["pay_frequency"].value == "Biweekly"

    def test_missing_gross_row_leaves_field_absent(self):
        page = make_page([[make_token("Employer", 1.0, 100, 100), make_token("Employee", 1.0, 800, 100)]])
        result = parse_paystub(page)
        assert "gross_pay_current" not in result

    def test_confidence_is_averaged_over_contributing_tokens(self):
        page = make_page(
            [
                [
                    make_token("Gross", 1.0, 100, 100),
                    make_token("Pay", 0.5, 170, 100),
                    make_token("100.00", 0.5, 400, 100),
                ]
            ]
        )
        result = parse_paystub(page)
        assert result["gross_pay_current"].confidence == 2.0 / 3


class TestParseBankStatement:
    def test_extracts_summary_row_by_four_money_values(self):
        rows = [
            [
                make_token("Beginning", 0.9, 100, 100),
                make_token("Total", 0.9, 300, 100),
                make_token("Total", 0.9, 500, 100),
                make_token("Ending", 0.9, 700, 100),
            ],
            [
                make_token("S6711.03", 0.8, 100, 200),
                make_token("S5403.24", 0.8, 300, 200),
                make_token("S2157.72", 0.8, 500, 200),
                make_token("S9956.55", 0.8, 700, 200),
            ],
        ]
        result = parse_bank_statement(make_page(rows))
        assert result["beginning_balance"].value == "6711.03"
        assert result["total_deposits"].value == "5403.24"
        assert result["total_withdrawals"].value == "2157.72"
        assert result["ending_balance"].value == "9956.55"

    def test_sums_multiple_payroll_deposit_rows(self):
        rows = [
            [
                make_token("2024-09-14", 0.9, 100, 100),
                make_token("Payroll", 0.9, 250, 100),
                make_token("Direct", 0.9, 350, 100),
                make_token("S2701.62", 0.9, 500, 100),
                make_token("S9071.29", 0.9, 700, 100),
            ],
            [
                make_token("2024-09-26", 0.9, 100, 200),
                make_token("Payroll", 0.9, 250, 200),
                make_token("Direct", 0.9, 350, 200),
                make_token("S2701.62", 0.9, 500, 200),
                make_token("S11601.82", 0.9, 700, 200),
            ],
        ]
        result = parse_bank_statement(make_page(rows))
        assert result["payroll_deposit_total"].value == "5403.24"

    def test_no_payroll_rows_leaves_field_absent(self):
        rows = [[make_token("Grocery", 0.9, 100, 100), make_token("S64.22", 0.9, 400, 100)]]
        result = parse_bank_statement(make_page(rows))
        assert "payroll_deposit_total" not in result


class TestParseW2:
    def test_extracts_employer_name_ein_and_box1(self):
        rows = [
            [
                make_token("EMPLOYER", 0.9, 100, 100),
                make_token("EMPLOYEE", 0.9, 800, 100),
            ],
            [
                make_token("Acme", 0.95, 100, 200),
                make_token("Corp", 0.9, 180, 200),
                make_token("John", 0.98, 800, 200),
                make_token("Doe", 0.97, 880, 200),
            ],
            [make_token("EIN:", 0.9, 100, 300), make_token("75-1234567", 0.85, 200, 300)],
            [
                make_token("Wages,", 0.8, 100, 400),
                make_token("tips,", 0.8, 170, 400),
                make_token("other", 0.8, 240, 400),
                make_token("compensation", 0.8, 310, 400),
                make_token("S92000.00", 0.75, 700, 400),
            ],
        ]
        result = parse_w2(make_page(rows))
        assert result["employer_name"].value == "Acme Corp"
        assert result["employer_ein"].value == "75-1234567"
        assert result["box1_wages"].value == "92000.00"

    def test_ein_row_not_confused_with_header_mentioning_ein(self):
        # The header row itself contains the word "EIN" (as in "AND EIN"),
        # which must not be mistaken for the actual EIN: NNN-NNNNNNN row.
        rows = [
            [
                make_token("EMPLOYER", 0.9, 100, 100),
                make_token("NAME", 0.9, 200, 100),
                make_token("AND", 0.9, 300, 100),
                make_token("EIN", 0.9, 380, 100),
            ],
            [make_token("EIN:", 0.9, 100, 300), make_token("12-3456789", 0.85, 200, 300)],
        ]
        result = parse_w2(make_page(rows))
        assert result["employer_ein"].value == "12-3456789"
