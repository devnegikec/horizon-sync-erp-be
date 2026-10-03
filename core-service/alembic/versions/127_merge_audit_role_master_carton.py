"""Merge the audit-role and master-carton estimation heads.

``120_add_master_carton_estimation_fields`` branched off
``119_add_packaging_unit_tracking`` while the main line continued through
``119_add_shortage_tracking`` → ``120_fix_shortage_history_fk`` → … →
``126_add_audit_log_role``. Both branches were applied independently, leaving
two heads and breaking ``alembic upgrade head``. This merge reunites them.

Revision ID: 127_merge_audit_role_master_carton
Revises: 126_add_audit_log_role, 120_add_master_carton_estimation_fields
Create Date: 2026-09-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "127_merge_audit_role_master_carton"
down_revision: str | Sequence[str] | None = (
    "126_add_audit_log_role",
    "120_add_master_carton_estimation_fields",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
