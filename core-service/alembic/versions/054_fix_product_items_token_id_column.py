"""fix product_items token_id column type

Revision ID: 055_fix_product_items_token_id_column
Revises: 054_add_qr_product_id_to_items
Create Date: 2026-05-26

The token_id column on product_items was VARCHAR(75) in the database but the
SQLAlchemy model defines it as Text. Generated QR URLs with ECDSA signatures
are ~150-200 characters, causing:

    psycopg2.errors.StringDataRightTruncation:
    value too long for type character varying(75)

This migration alters the column to TEXT (unlimited length) to match the model.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "055_fix_product_items_token_id_column"
down_revision = "054_add_qr_product_id_to_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER the column from VARCHAR(75) to TEXT.
    # USING cast is not needed — VARCHAR is implicitly castable to TEXT in Postgres.
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    op.alter_column(
        "product_items",
        "token_id",
        existing_type=sa.String(75),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Truncate back to 75 chars on downgrade (data loss possible if any value > 75 chars).
    op.alter_column(
        "product_items",
        "token_id",
        existing_type=sa.Text(),
        type_=sa.String(75),
        existing_nullable=True,
        postgresql_using="token_id::character varying(75)",
    )
