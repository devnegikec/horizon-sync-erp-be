"""Repair the audit log role column when the original migration was skipped.

The original ``126_add_audit_log_role`` migration is guarded by the presence of
the ``audit_logs`` table.  Some databases were stamped past that revision while
the table was absent or created later, leaving the ORM model ahead of the live
schema.  This migration checks the live schema again so the repair is applied
even when Alembic already considers revision 126 complete.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_index, has_table


revision: str = "136_repair_audit_log_role"
down_revision: str | Sequence[str] | None = (
    "120_add_qseal_product_activated_notification_type",
    "135_add_bin_stock_parent_qr_flag",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ensure the column and its filtering index exist on the live database."""
    if not has_table("audit_logs"):
        return

    if not has_column("audit_logs", "role"):
        op.add_column(
            "audit_logs",
            sa.Column("role", sa.String(50), nullable=True),
        )

    if not has_index("audit_logs", "ix_audit_logs_role"):
        op.create_index("ix_audit_logs_role", "audit_logs", ["role"])


def downgrade() -> None:
    """Remove only objects created by this repair migration."""
    if not has_table("audit_logs"):
        return

    if has_index("audit_logs", "ix_audit_logs_role"):
        op.drop_index("ix_audit_logs_role", table_name="audit_logs")

    if has_column("audit_logs", "role"):
        op.drop_column("audit_logs", "role")
