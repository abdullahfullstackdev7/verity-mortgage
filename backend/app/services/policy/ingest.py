"""One-time (idempotent) ingestion of the internal underwriting guidelines
corpus into `policy_chunks`, embedded with the same local sentence-
transformers model used elsewhere in the pipeline. This is what powers the
retrieval-augmented context in Phase 7's summary generation.

    python -m backend.app.services.policy.ingest
"""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.db.base import SessionLocal
from backend.app.db.models.policy_chunk import PolicyChunk
from backend.app.services.extraction.embedding import embed_texts

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_GUIDELINES_PATH = REPO_ROOT / "data" / "policy_guidelines" / "underwriting_guidelines.md"

_HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def split_into_chunks(markdown_text: str) -> list[str]:
    """Split a markdown doc into one chunk per `##` section (heading +
    body), dropping the top-level `#` preamble."""
    matches = list(_HEADING_RE.finditer(markdown_text))
    chunks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        chunks.append(markdown_text[start:end].strip())
    return chunks


def ingest_policy_guidelines(
    db: Session, path: Path = DEFAULT_GUIDELINES_PATH, force: bool = False
) -> int:
    """Embed and store each section of the guidelines doc as a PolicyChunk.
    Idempotent: a no-op if chunks for this source doc already exist, unless
    force=True (in which case they're replaced)."""
    source_doc = path.name

    existing_count = (
        db.query(PolicyChunk).filter(PolicyChunk.source_doc == source_doc).count()
    )
    if existing_count and not force:
        return existing_count

    if existing_count:
        db.query(PolicyChunk).filter(PolicyChunk.source_doc == source_doc).delete()
        db.commit()

    chunks = split_into_chunks(path.read_text(encoding="utf-8"))
    vectors = embed_texts(chunks)

    for chunk_text, vector in zip(chunks, vectors):
        db.add(PolicyChunk(source_doc=source_doc, chunk_text=chunk_text, embedding=vector))
    db.commit()

    return len(chunks)


def main() -> int:
    db = SessionLocal()
    try:
        count = ingest_policy_guidelines(db, force=True)
    finally:
        db.close()
    print(f"Ingested {count} policy chunks from {DEFAULT_GUIDELINES_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
