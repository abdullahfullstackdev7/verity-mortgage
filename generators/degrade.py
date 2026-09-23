"""Optional scan-realism pass: degrade a subset of generated PDFs so the
Phase 5 OCR pipeline has something closer to a real scanned document to
stress-test against (slight rotation, sensor noise, JPEG re-compression).

Output is saved as JPEG page images rather than PDF, since the degradation
is a rasterization artifact simulation, not a vector document edit.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from PIL import Image

MAX_ROTATION_DEGREES = 3.0
NOISE_STD_DEV = 6.0
JPEG_QUALITY = 55
RENDER_SCALE = 2.0


def _rng_seed(applicant_id: str, doc_type: str) -> int:
    digest = hashlib.sha256(f"degrade:{applicant_id}:{doc_type}".encode()).hexdigest()
    return int(digest[:8], 16)


def _render_first_page(pdf_path: Path) -> Image.Image:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        page = pdf[0]
        bitmap = page.render(scale=RENDER_SCALE)
        return bitmap.to_pil().convert("RGB")
    finally:
        pdf.close()


def _apply_rotation(image: Image.Image, rng: np.random.Generator) -> Image.Image:
    angle = float(rng.uniform(-MAX_ROTATION_DEGREES, MAX_ROTATION_DEGREES))
    return image.rotate(angle, expand=True, fillcolor="white")


def _apply_noise(image: Image.Image, rng: np.random.Generator) -> Image.Image:
    arr = np.asarray(image).astype(np.int16)
    noise = rng.normal(0, NOISE_STD_DEV, arr.shape)
    noisy = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy, mode="RGB")


def _apply_jpeg_recompression(image: Image.Image) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def degrade_pdf(pdf_path: Path, output_path: Path, applicant_id: str, doc_type: str) -> Path:
    """Render `pdf_path`'s first page, degrade it, and save a JPEG to
    `output_path`. Deterministic per (applicant_id, doc_type)."""
    seed = _rng_seed(applicant_id, doc_type)
    rng = np.random.default_rng(seed)

    image = _render_first_page(pdf_path)
    image = _apply_rotation(image, rng)
    image = _apply_noise(image, rng)
    image = _apply_jpeg_recompression(image)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="JPEG", quality=JPEG_QUALITY)
    return output_path
