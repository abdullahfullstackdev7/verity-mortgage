"""Local, free HuggingFace sentence-transformers embeddings, used to enable
fuzzy matching of noisy OCR text (e.g. "ACME CORP" vs "Acme Corporation")
via cosine similarity in later phases, instead of exact string comparison.
"""

from __future__ import annotations

from functools import lru_cache

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=False)
    return [v.tolist() for v in vectors]
