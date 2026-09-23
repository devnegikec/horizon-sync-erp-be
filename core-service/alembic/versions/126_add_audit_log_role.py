"""Add ``role`` column to ``audit_logs``.

Captures the acting user's role (the JWT ``user_type`` claim, e.g.
``system_admin``, ``organization_admin``, ``user``) at write time so the
audit UI can filter events by user role. Historic rows keep ``role = NULL``.

Revision ID: 126_add_audit_log_role
Revises: 125_bin_stock_status_unique
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_index, has_table

revision: str = "126_add_audit_log_role"
down_revision: str | Sequence[str] | None = "125_bin_stock_status_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_table("audit_logs"):
        return

    if not has_column("audit_logs", "role"):
        op.add_column(
            "audit_logs",
            sa.Column("role", sa.String(50), nullable=True),
        )

    # Guarded separately from the column: the two can exist independently on a
    # database where this migration was partly applied. Nesting the index inside
    # the column guard would silently leave role filtering unindexed.
    if not has_index("audit_logs", "ix_audit_logs_role"):
        op.create_index("ix_audit_logs_role", "audit_logs", ["role"])


def downgrade() -> None:
    if not has_table("audit_logs"):
        return

    # The index may be absent while the column is present, so it needs its own
    # guard -- an unconditional drop would raise and abort the downgrade.
    if has_index("audit_logs", "ix_audit_logs_role"):
        op.drop_index("ix_audit_logs_role", table_name="audit_logs")

    if has_column("audit_logs", "role"):
        op.drop_column("audit_logs", "role")
