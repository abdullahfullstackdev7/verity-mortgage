from __future__ import annotations

import pytest
from conftest import requires_db

from backend.app.db.base import SessionLocal
from backend.app.db.models.policy_chunk import PolicyChunk
from backend.app.services.extraction.embedding import embed_text
from backend.app.services.policy.retrieval import retrieve_relevant_chunks

pytestmark = requires_db

SOURCE_DOC = "test_retrieval_corpus.md"


@pytest.fixture
def sample_chunks():
    db = SessionLocal()
    texts = {
        "income": "Income verification compares pay stub gross pay against stated income with a tolerance band.",
        "employer": (
            "Employer identity is checked using semantic similarity between the stated and extracted employer name."
        ),
        "cooking": "This section is entirely about baking sourdough bread and has nothing to do with underwriting.",
    }
    for key, text in texts.items():
        db.add(PolicyChunk(source_doc=SOURCE_DOC, chunk_text=f"## {key}\n{text}", embedding=embed_text(text)))
    db.commit()

    yield

    db.query(PolicyChunk).filter(PolicyChunk.source_doc == SOURCE_DOC).delete()
    db.commit()
    db.close()


class TestRetrieveRelevantChunks:
    def test_income_query_ranks_income_chunk_first(self, sample_chunks):
        db = SessionLocal()
        results = retrieve_relevant_chunks(db, "income_paystub major discrepancy", top_k=1)
        db.close()
        assert len(results) == 1
        assert "income" in results[0].chunk_text.lower()

    def test_employer_query_ranks_employer_chunk_first(self, sample_chunks):
        db = SessionLocal()
        results = retrieve_relevant_chunks(db, "employer_name_w2 minor discrepancy", top_k=1)
        db.close()
        assert "employer" in results[0].chunk_text.lower()

    def test_unrelated_chunk_is_not_top_result(self, sample_chunks):
        db = SessionLocal()
        results = retrieve_relevant_chunks(db, "debt_to_income_ratio major discrepancy", top_k=2)
        db.close()
        assert "sourdough" not in results[0].chunk_text.lower()

    def test_empty_query_returns_nothing(self, sample_chunks):
        db = SessionLocal()
        results = retrieve_relevant_chunks(db, "   ", top_k=2)
        db.close()
        assert results == []

    def test_top_k_is_respected(self, sample_chunks):
        db = SessionLocal()
        results = retrieve_relevant_chunks(db, "income", top_k=2)
        db.close()
        assert len(results) == 2
