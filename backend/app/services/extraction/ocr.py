"""OCR wrapper around easyocr, plus row/column reconstruction so downstream
parsers can do layout-anchor extraction instead of guessing from raw
detection order.

The project plan names Tesseract/PaddleOCR. Tesseract's binary isn't
installed on this machine (and, like WeasyPrint in Phase 2, would need a
system-wide installer to add), and PaddleOCR's Windows install is heavy and
finicky. easyocr is used instead: pip-installable, no external binary,
comparable accuracy for this use case.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium

RENDER_SCALE = 2.0
ROW_Y_TOLERANCE_FRACTION = 0.012  # of page height; tokens within this band are "same row"


@dataclass(frozen=True)
class Token:
    text: str
    confidence: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @property
    def x_center(self) -> float:
        return (self.x_min + self.x_max) / 2

    @property
    def y_center(self) -> float:
        return (self.y_min + self.y_max) / 2


@dataclass(frozen=True)
class OcrPage:
    tokens: list[Token]
    width: int
    height: int

    @property
    def mean_confidence(self) -> float:
        if not self.tokens:
            return 0.0
        return sum(t.confidence for t in self.tokens) / len(self.tokens)


@lru_cache(maxsize=1)
def _get_reader():
    import easyocr

    return easyocr.Reader(["en"], gpu=False, verbose=False)


def render_first_page(pdf_path: Path) -> np.ndarray:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        image = pdf[0].render(scale=RENDER_SCALE).to_pil().convert("RGB")
        return np.array(image)
    finally:
        pdf.close()


def run_ocr(pdf_path: Path) -> OcrPage:
    image = render_first_page(pdf_path)
    height, width = image.shape[:2]

    reader = _get_reader()
    results = reader.readtext(image, detail=1)

    tokens = []
    for bbox, text, confidence in results:
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        tokens.append(
            Token(
                text=text,
                confidence=float(confidence),
                x_min=min(xs),
                x_max=max(xs),
                y_min=min(ys),
                y_max=max(ys),
            )
        )
    return OcrPage(tokens=tokens, width=width, height=height)


def group_rows(page: OcrPage) -> list[list[Token]]:
    """Cluster tokens into visual rows by y-position, then order each row
    left to right. This reconstructs reading order far more reliably than
    easyocr's raw detection order for a fixed, table-heavy layout."""
    if not page.tokens:
        return []

    tolerance = page.height * ROW_Y_TOLERANCE_FRACTION
    sorted_tokens = sorted(page.tokens, key=lambda t: t.y_center)

    rows: list[list[Token]] = []
    current_row: list[Token] = [sorted_tokens[0]]
    current_y = sorted_tokens[0].y_center

    for token in sorted_tokens[1:]:
        if abs(token.y_center - current_y) <= tolerance:
            current_row.append(token)
        else:
            rows.append(sorted(current_row, key=lambda t: t.x_center))
            current_row = [token]
            current_y = token.y_center
    rows.append(sorted(current_row, key=lambda t: t.x_center))

    return rows


def row_text(row: list[Token]) -> str:
    return " ".join(t.text for t in row)


def full_text(page: OcrPage) -> str:
    return "\n".join(row_text(row) for row in group_rows(page))
