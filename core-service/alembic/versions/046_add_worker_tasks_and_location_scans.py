"""Add worker_tasks and location_scans tables

Revision ID: 046_add_worker_tasks_and_location_scans
Revises: 045_add_gate_verification_and_dispatch_tables
Create Date: 2025-07-14

Creates the worker task tracking and location scan time tracking tables
for the warehouse QR-based workflow:

- worker_tasks: Tracks put-away and pick tasks assigned to workers
- location_scans: Records start/finish QR scans at bin locations for time tracking

Requirements: 16.1, 16.2, 17.5
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "046_add_worker_tasks_and_location_scans"
down_revision = "045_add_gate_verification_and_dispatch_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── worker_tasks ───────────────────────────────────────────────
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    op.create_table(
        "worker_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("task_type", sa.String(20), nullable=False),
        sa.Column(
            "worker_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "reference_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="assigned",
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "task_type IN ('put_away', 'pick')",
            name="chk_task_type",
        ),
        sa.CheckConstraint(
            "status IN ('assigned', 'in_progress', 'completed', 'cancelled')",
            name="chk_task_status",
        ),
    )

    # Indexes for worker_tasks
    op.create_index("idx_wt_org", "worker_tasks", ["organization_id"])
    op.create_index("idx_wt_worker", "worker_tasks", ["worker_id"])
    op.create_index("idx_wt_status", "worker_tasks", ["status"])
    op.create_index("idx_wt_type", "worker_tasks", ["task_type"])

    # ── location_scans ─────────────────────────────────────────────
    op.create_table(
        "location_scans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "worker_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("worker_tasks.id"),
            nullable=False,
        ),
        sa.Column("location_code", sa.String(255), nullable=False),
        sa.Column("scan_type", sa.String(10), nullable=False),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "scan_type IN ('start', 'finish')",
            name="chk_scan_type",
        ),
    )

    # Indexes for location_scans
    op.create_index("idx_ls_org", "location_scans", ["organization_id"])
    op.create_index("idx_ls_task", "location_scans", ["worker_task_id"])
    op.create_index("idx_ls_type", "location_scans", ["scan_type"])


def downgrade() -> None:
    # Drop indexes and tables in reverse order
    op.drop_index("idx_ls_type", table_name="location_scans")
    op.drop_index("idx_ls_task", table_name="location_scans")
    op.drop_index("idx_ls_org", table_name="location_scans")
    op.drop_table("location_scans")

    op.drop_index("idx_wt_type", table_name="worker_tasks")
    op.drop_index("idx_wt_status", table_name="worker_tasks")
    op.drop_index("idx_wt_worker", table_name="worker_tasks")
    op.drop_index("idx_wt_org", table_name="worker_tasks")
    op.drop_table("worker_tasks")
