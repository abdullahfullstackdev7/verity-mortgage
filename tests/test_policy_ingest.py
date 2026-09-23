from __future__ import annotations

import pytest

from backend.app.db.base import SessionLocal
from backend.app.db.models.policy_chunk import PolicyChunk
from backend.app.services.policy.ingest import ingest_policy_guidelines, split_into_chunks
from conftest import requires_db

SAMPLE_MD = """# Title

Preamble text that should be dropped.

## First Section

Body of the first section.

## Second Section

Body of the second section.
Spanning two lines.
"""


class TestSplitIntoChunks:
    def test_splits_by_h2_heading_and_drops_preamble(self):
        chunks = split_into_chunks(SAMPLE_MD)
        assert len(chunks) == 2
        assert chunks[0].startswith("## First Section")
        assert "Preamble" not in chunks[0]

    def test_each_chunk_includes_its_body(self):
        chunks = split_into_chunks(SAMPLE_MD)
        assert "Body of the first section." in chunks[0]
        assert "Spanning two lines." in chunks[1]

    def test_no_headings_returns_empty(self):
        assert split_into_chunks("# Just a title\n\nNo sections here.") == []


@pytest.fixture
def fixture_md_path(tmp_path):
    path = tmp_path / "test_guidelines.md"
    path.write_text(SAMPLE_MD, encoding="utf-8")
    return path


@requires_db
class TestIngestPolicyGuidelines:
    def test_ingests_one_chunk_per_section(self, fixture_md_path):
        db = SessionLocal()
        try:
            count = ingest_policy_guidelines(db, path=fixture_md_path)
            assert count == 2
            rows = (
                db.query(PolicyChunk)
                .filter(PolicyChunk.source_doc == fixture_md_path.name)
                .all()
            )
            assert len(rows) == 2
            assert len(rows[0].embedding) == 384
        finally:
            db.query(PolicyChunk).filter(
                PolicyChunk.source_doc == fixture_md_path.name
            ).delete()
            db.commit()
            db.close()

    def test_second_call_without_force_is_a_no_op(self, fixture_md_path):
        db = SessionLocal()
        try:
            ingest_policy_guidelines(db, path=fixture_md_path)
            first_ids = {
                row.id
                for row in db.query(PolicyChunk).filter(
                    PolicyChunk.source_doc == fixture_md_path.name
                )
            }

            ingest_policy_guidelines(db, path=fixture_md_path)
            second_ids = {
                row.id
                for row in db.query(PolicyChunk).filter(
                    PolicyChunk.source_doc == fixture_md_path.name
                )
            }
            assert first_ids == second_ids
        finally:
            db.query(PolicyChunk).filter(
                PolicyChunk.source_doc == fixture_md_path.name
            ).delete()
            db.commit()
            db.close()

    def test_force_replaces_rows(self, fixture_md_path):
        db = SessionLocal()
        try:
            ingest_policy_guidelines(db, path=fixture_md_path)
            first_ids = {
                row.id
                for row in db.query(PolicyChunk).filter(
                    PolicyChunk.source_doc == fixture_md_path.name
                )
            }

            ingest_policy_guidelines(db, path=fixture_md_path, force=True)
            second_ids = {
                row.id
                for row in db.query(PolicyChunk).filter(
                    PolicyChunk.source_doc == fixture_md_path.name
                )
            }
            assert first_ids.isdisjoint(second_ids)
        finally:
            db.query(PolicyChunk).filter(
                PolicyChunk.source_doc == fixture_md_path.name
            ).delete()
            db.commit()
            db.close()
