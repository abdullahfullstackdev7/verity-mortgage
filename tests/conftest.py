from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from backend.app.db.base import engine


def db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


requires_db = pytest.mark.skipif(
    not db_available(),
    reason="Postgres not reachable; run `docker compose up -d` to enable DB tests.",
)
