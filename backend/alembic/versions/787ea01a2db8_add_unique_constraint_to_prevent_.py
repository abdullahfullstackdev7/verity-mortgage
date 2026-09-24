"""add unique constraint to prevent duplicate extraction rows

Revision ID: 787ea01a2db8
Revises: e9c7c045159b
Create Date: 2026-09-24 07:54:33.251835

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '787ea01a2db8'
down_revision: Union[str, None] = 'e9c7c045159b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_document_embeddings_document_id_field_name', 'document_embeddings', ['document_id', 'field_name'])
    op.create_unique_constraint('uq_extracted_fields_document_id_field_name', 'extracted_fields', ['document_id', 'field_name'])


def downgrade() -> None:
    op.drop_constraint('uq_extracted_fields_document_id_field_name', 'extracted_fields', type_='unique')
    op.drop_constraint('uq_document_embeddings_document_id_field_name', 'document_embeddings', type_='unique')
