"""Shared Jinja2 + xhtml2pdf rendering helper for the document generators.

WeasyPrint (the renderer named in the project plan) depends on the native
GTK3 stack (Pango/cairo/gobject) which is not installed on this machine and
would require a system-wide installer to add. xhtml2pdf is a pure-Python,
open-source HTML-to-PDF renderer with no native dependencies, so it is used
here instead; it supports the CSS subset (tables, borders, simple text
styling) these templates rely on.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "data" / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_pdf(template_name: str, context: dict, output_path: Path) -> None:
    """Render a Jinja2 template with `context` to a PDF at `output_path`."""
    template = _env.get_template(template_name)
    html = template.render(**context)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        result = pisa.CreatePDF(html, dest=f)

    if result.err:
        raise RuntimeError(f"Failed to render {template_name} to {output_path}")
