"""Merge: single parent l2m3n4o5p6q7r8; applies 009 DDL for DBs that skipped 009

Revision ID: 010_merge
Revises: l2m3n4o5p6q7r8
Create Date: 2026-02-24

Single parent so DBs at f6g7h8i9j0k1 (accounts branch) can upgrade without 009 in
alembic_version. Applies 009's item discount columns idempotently so schema matches.
"""

import sqlalchemy as sa
from alembic import op

revision = "010_merge"
down_revision = ("l2m3n4o5p6q7r8",)
branch_labels = None
depends_on = None


def _ensure_discount_columns(conn, table_name: str, inspector) -> None:
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    if "discount_type" not in columns:
        op.add_column(
            table_name,
            sa.Column("discount_type", sa.String(20), nullable=True, server_default="percentage"),
        )
    if "discount_value" not in columns:
        op.add_column(
            table_name,
            sa.Column("discount_value", sa.Numeric(15, 2), nullable=True, server_default="0"),
        )
    if "discount_amount" not in columns:
        op.add_column(
            table_name,
            sa.Column("discount_amount", sa.Numeric(15, 2), nullable=True, server_default="0"),
        )


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    _ensure_discount_columns(conn, "quotation_items", inspector)
    _ensure_discount_columns(conn, "sales_order_items", inspector)


def downgrade() -> None:
    pass
