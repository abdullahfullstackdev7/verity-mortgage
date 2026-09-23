"""Field-level encryption at rest via PostgreSQL's pgcrypto extension.

`EncryptedNumeric` is a SQLAlchemy TypeDecorator: application code still
reads and writes plain Python numbers through the ORM as normal, but the
actual column is `bytea`, and every INSERT/SELECT wraps the value in
`pgp_sym_encrypt`/`pgp_sym_decrypt` at the SQL level. A raw `SELECT` of the
column (or a stolen DB dump) yields ciphertext, not the figure.

This only covers Applicant's stated financial figures ("stated income" is
the plan's explicit example). It does not cover free-text extracted
document fields, which share one polymorphic text column across every
document type and field name -- encrypting that column uniformly would
block the substring/anchor-based parsing Phase 5 depends on without a much
larger redesign, so it's left as a documented gap rather than a silent one.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.types import LargeBinary, TypeDecorator

from backend.app.core.config import settings


class EncryptedNumeric(TypeDecorator):
    impl = LargeBinary
    cache_ok = True

    def __init__(self, precision: int = 14, scale: int = 2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.precision = precision
        self.scale = scale

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def bind_expression(self, bindvalue):
        # type_coerce is a Python-side typing hint (no SQL CAST emitted),
        # so the driver still sends the already-stringified value as text
        # for pgp_sym_encrypt to consume.
        return sa.func.pgp_sym_encrypt(sa.type_coerce(bindvalue, sa.Text), settings.db_encryption_key)

    def column_expression(self, col):
        return sa.cast(
            sa.func.pgp_sym_decrypt(col, settings.db_encryption_key),
            sa.Numeric(self.precision, self.scale),
        )
