"""Add Item approval-workflow columns (Phase 5).

Revision ID: 084_add_item_approval_columns
Revises: 083_drop_item_qseal_sync_columns
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.alembic_guards import has_column

revision: str = "084_add_item_approval_columns"
down_revision: str | Sequence[str] | None = "083_drop_item_qseal_sync_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for col_name, col in (
        ("submitted_by", sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=True)),
        ("submitted_at", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True)),
        ("approved_by", sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True)),
        ("approved_at", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)),
        ("rejection_reason", sa.Column("rejection_reason", sa.Text(), nullable=True)),
    ):
        if not has_column("items", col_name):
            op.add_column("items", col)


def downgrade() -> None:
    for col_name in (
        "submitted_by",
        "submitted_at",
        "approved_by",
        "approved_at",
        "rejection_reason",
    ):
        if has_column("items", col_name):
            op.drop_column("items", col_name)
