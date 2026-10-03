"""Add task-accept columns + worker_sessions + lockout columns

Revision ID: 099_add_task_accept_and_worker_sessions
Revises: 098_add_erp_sync_queue
Create Date: 2026-08-30

PR-14 / T-14:
- ``pick_lists.accepted_at`` / ``accepted_by`` for task accept (WF-010).
- ``wms_workers.failed_login_attempts`` / ``locked_until`` for login lockout (WF-009).
- ``worker_sessions`` table for idle-timeout session tracking (WF-009).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_table

revision: str = "099_add_task_accept_and_worker_sessions"
down_revision: str | Sequence[str] | None = "098_add_erp_sync_queue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if has_table("pick_lists"):
        if not has_column("pick_lists", "accepted_at"):
            op.add_column(
                "pick_lists",
                sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            )
        if not has_column("pick_lists", "accepted_by"):
            op.add_column(
                "pick_lists",
                sa.Column("accepted_by", postgresql.UUID(as_uuid=True), nullable=True),
            )

    if has_table("wms_workers"):
        if not has_column("wms_workers", "failed_login_attempts"):
            op.add_column(
                "wms_workers",
                sa.Column(
                    "failed_login_attempts",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                ),
            )
        if not has_column("wms_workers", "locked_until"):
            op.add_column(
                "wms_workers",
                sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            )

    if not has_table("worker_sessions"):
        op.create_table(
            "worker_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_worker_sessions_organization_id",
            "worker_sessions",
            ["organization_id"],
        )
        op.create_index("ix_worker_sessions_worker_id", "worker_sessions", ["worker_id"])
        op.create_index("ix_worker_sessions_status", "worker_sessions", ["status"])


def downgrade() -> None:
    if has_table("worker_sessions"):
        op.drop_index("ix_worker_sessions_status", table_name="worker_sessions")
        op.drop_index("ix_worker_sessions_worker_id", table_name="worker_sessions")
        op.drop_index(
            "ix_worker_sessions_organization_id", table_name="worker_sessions"
        )
        op.drop_table("worker_sessions")

    if has_column("wms_workers", "locked_until"):
        op.drop_column("wms_workers", "locked_until")
    if has_column("wms_workers", "failed_login_attempts"):
        op.drop_column("wms_workers", "failed_login_attempts")

    if has_column("pick_lists", "accepted_by"):
        op.drop_column("pick_lists", "accepted_by")
    if has_column("pick_lists", "accepted_at"):
        op.drop_column("pick_lists", "accepted_at")
