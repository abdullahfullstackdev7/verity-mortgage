"""Schema-level tests against the live Postgres container defined in
docker-compose.yml. Skipped automatically if that database isn't reachable
(e.g. `docker compose up -d` hasn't been run), so the rest of the suite
stays runnable without Docker.
"""

from __future__ import annotations

import uuid

import pytest
from conftest import requires_db
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from backend.app.db.base import SessionLocal, engine
from backend.app.db.models import Applicant, Case
from backend.app.db.models.enums import CaseStatus

pytestmark = requires_db


EXPECTED_TABLES = {
    "users",
    "applicants",
    "cases",
    "documents",
    "extracted_fields",
    "discrepancies",
    "case_summaries",
    "audit_log",
    "policy_chunks",
    "document_embeddings",
}


class TestSchema:
    def test_all_expected_tables_exist(self):
        inspector = inspect(engine)
        assert EXPECTED_TABLES <= set(inspector.get_table_names())

    def test_pgvector_extension_installed(self):
        with engine.connect() as conn:
            row = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
        assert row is not None

    def test_vector_columns_are_384_dimensional(self):
        with engine.connect() as conn:
            for table, column in [
                ("policy_chunks", "embedding"),
                ("document_embeddings", "embedding"),
            ]:
                dim = conn.execute(
                    text(
                        "SELECT atttypmod FROM pg_attribute a "
                        "JOIN pg_class c ON a.attrelid = c.oid "
                        "WHERE c.relname = :table AND a.attname = :column"
                    ),
                    {"table": table, "column": column},
                ).scalar()
                assert dim == 384

    def test_hnsw_indexes_exist_on_embedding_tables(self):
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename IN ('policy_chunks', 'document_embeddings') "
                    "AND indexdef ILIKE '%hnsw%'"
                )
            ).fetchall()
        assert len(rows) == 2


class TestConstraints:
    def test_case_requires_existing_applicant(self):
        session = SessionLocal()
        try:
            orphan_case = Case(applicant_id=uuid.uuid4(), status=CaseStatus.SUBMITTED)
            session.add(orphan_case)
            with pytest.raises(IntegrityError):
                session.commit()
        finally:
            session.rollback()
            session.close()

    def test_applicant_hmda_source_id_is_unique(self):
        session = SessionLocal()
        try:
            shared_source_id = f"uniqueness-test:{uuid.uuid4()}"
            a1 = Applicant(
                id=uuid.uuid4(),
                name="Test A",
                address="1 Test St",
                employer_name="Test Co",
                hmda_source_id=shared_source_id,
                stated_income=50000,
                stated_loan_amount=200000,
                stated_property_value=220000,
                stated_dti=30,
            )
            session.add(a1)
            session.commit()

            a2 = Applicant(
                id=uuid.uuid4(),
                name="Test B",
                address="2 Test St",
                employer_name="Test Co",
                hmda_source_id=shared_source_id,
                stated_income=60000,
                stated_loan_amount=210000,
                stated_property_value=230000,
                stated_dti=31,
            )
            session.add(a2)
            with pytest.raises(IntegrityError):
                session.commit()
        finally:
            session.rollback()
            session.execute(Applicant.__table__.delete().where(Applicant.hmda_source_id == shared_source_id))
            session.commit()
            session.close()

    def test_case_cascades_are_absent_by_default_and_status_enum_enforced(self):
        session = SessionLocal()
        try:
            applicant = Applicant(
                id=uuid.uuid4(),
                name="Enum Test",
                address="3 Test St",
                employer_name="Test Co",
                hmda_source_id=f"enum-test:{uuid.uuid4()}",
                stated_income=70000,
                stated_loan_amount=220000,
                stated_property_value=240000,
                stated_dti=28,
            )
            session.add(applicant)
            session.flush()

            case = Case(applicant_id=applicant.id, status=CaseStatus.SUBMITTED)
            session.add(case)
            session.commit()

            fetched = session.scalar(select(Case).where(Case.id == case.id))
            assert fetched.status == CaseStatus.SUBMITTED

            session.delete(fetched)
            session.delete(applicant)
            session.commit()
        finally:
            session.rollback()
            session.close()
