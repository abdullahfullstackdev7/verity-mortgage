"""Top-k retrieval of relevant policy guideline chunks by cosine similarity,
using pgvector's native distance operator so the search runs in Postgres
rather than pulling every chunk into Python.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.db.models.policy_chunk import PolicyChunk
from backend.app.services.extraction.embedding import embed_text

DEFAULT_TOP_K = 2


def retrieve_relevant_chunks(db: Session, query_text: str, top_k: int = DEFAULT_TOP_K) -> list[PolicyChunk]:
    if not query_text.strip():
        return []

    query_vector = embed_text(query_text)
    return db.query(PolicyChunk).order_by(PolicyChunk.embedding.cosine_distance(query_vector)).limit(top_k).all()
