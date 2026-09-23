"""enable pgcrypto and encrypt applicant financial fields

Revision ID: e9c7c045159b
Revises: 54a9e3082e44
Create Date: 2026-09-24 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

from backend.app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "e9c7c045159b"
down_revision: str | None = "54a9e3082e44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (column, precision, scale) for applicants' stated financial figures.
_ENCRYPTED_COLUMNS = [
    ("stated_income", 14, 2),
    ("stated_loan_amount", 14, 2),
    ("stated_property_value", 14, 2),
    ("stated_dti", 5, 2),
]


def _quoted_key() -> str:
    # Postgres can't infer the parameter type of a bind param passed
    # through ALTER ... USING pgp_sym_encrypt(...), so the key is embedded
    # as a dollar-quoted literal instead of a bind parameter. It comes from
    # trusted server-side settings, not user input, so this is safe -- and
    # dollar-quoting means no escaping is needed regardless of its content.
    return f"$enc_key${settings.db_encryption_key}$enc_key$"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    key_literal = _quoted_key()
    for column, _precision, _scale in _ENCRYPTED_COLUMNS:
        op.execute(
            f"ALTER TABLE applicants "
            f"ALTER COLUMN {column} TYPE bytea "
            f"USING pgp_sym_encrypt({column}::text, {key_literal})"
        )


def downgrade() -> None:
    key_literal = _quoted_key()
    for column, precision, scale in _ENCRYPTED_COLUMNS:
        op.execute(
            f"ALTER TABLE applicants "
            f"ALTER COLUMN {column} TYPE numeric({precision}, {scale}) "
            f"USING CAST(pgp_sym_decrypt({column}, {key_literal}) AS numeric({precision}, {scale}))"
        )

    # NOTE: pgcrypto is left installed on downgrade since other objects in
    # the database may depend on it; dropping extensions defensively is out
    # of scope for a per-table downgrade.
