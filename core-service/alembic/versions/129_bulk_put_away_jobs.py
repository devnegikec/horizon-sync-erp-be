"""Bulk put-away background jobs table (async bulk completion).

Tracks async bulk put-away requests so a scan device can enqueue a large
completion and poll for the per-item result instead of waiting on a long
synchronous request.

Revision ID: 129_bulk_put_away_jobs
Revises: 128_qr_scan_event_document_fks
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table

revision: str = "129_bulk_put_away_jobs"
down_revision: str | Sequence[str] | None = "128_qr_scan_event_document_fks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if has_table("bulk_put_away_jobs"):
        return

    op.create_table(
        "bulk_put_away_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("put_away_list_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("request_data", postgresql.JSONB(), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_bulk_put_away_jobs_org",
        "bulk_put_away_jobs",
        ["organization_id"],
    )
    op.create_index(
        "ix_bulk_put_away_jobs_status",
        "bulk_put_away_jobs",
        ["status"],
    )
    op.create_index(
        "ix_bulk_put_away_jobs_list",
        "bulk_put_away_jobs",
        ["put_away_list_id"],
    )


def downgrade() -> None:
    if has_table("bulk_put_away_jobs"):
        op.drop_table("bulk_put_away_jobs")
