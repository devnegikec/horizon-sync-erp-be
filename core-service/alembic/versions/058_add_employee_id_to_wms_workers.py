"""Add employee_id to wms_workers

Revision ID: 058_add_employee_id_to_wms_workers
Revises: 057_add_wms_workers_and_devices
Create Date: 2026-06-12

Adds a unique, nullable employee_id column to wms_workers.
The column is unique per organization (enforced at the application layer via
a partial unique index) and can be supplied by the admin at worker creation
time.
"""

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_table

revision = "058_add_employee_id_to_wms_workers"
down_revision = "057_add_wms_workers_and_devices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if has_table("wms_workers"):
        # Add the employee_id column (nullable so existing rows are unaffected)
        op.add_column(
            "wms_workers",
            sa.Column("employee_id", sa.String(100), nullable=True),
        )
        # Unique per (organization_id, employee_id) — only when employee_id IS NOT NULL
        op.create_index(
            "uq_wms_worker_employee_id_org",
            "wms_workers",
            ["organization_id", "employee_id"],
            unique=True,
            postgresql_where=sa.text("employee_id IS NOT NULL"),
        )


def downgrade() -> None:
    if has_table("wms_workers"):
        op.drop_index("uq_wms_worker_employee_id_org", table_name="wms_workers")
        op.drop_column("wms_workers", "employee_id")
