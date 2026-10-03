"""Add erp_sync_messages table + erp_sync_failed notification type

Revision ID: 098_add_erp_sync_queue
Revises: 097_add_pick_list_priority
Create Date: 2026-08-30

Adds the outbound ERP sync queue (PR-13 / T-13, WF-022) and extends the
``notificationtype`` enum with ``erp_sync_failed`` so exhausted sync retries
raise a failure alert (ALT-009) via the existing NotificationService.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table, has_type

revision: str = "098_add_erp_sync_queue"
down_revision: str | Sequence[str] | None = "097_add_pick_list_priority"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if has_type("notificationtype"):
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = 'notificationtype'
                      AND e.enumlabel = 'erp_sync_failed'
                ) THEN
                    ALTER TYPE notificationtype ADD VALUE 'erp_sync_failed';
                END IF;
            END $$;
            """
        )

    if not has_table("erp_sync_messages"):
        op.create_table(
            "erp_sync_messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("entity_type", sa.String(length=50), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("operation", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("pick_list_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("dispatch_record_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_erp_sync_messages_organization_id",
            "erp_sync_messages",
            ["organization_id"],
        )
        op.create_index(
            "ix_erp_sync_messages_entity_type",
            "erp_sync_messages",
            ["entity_type"],
        )
        op.create_index(
            "ix_erp_sync_messages_entity_id",
            "erp_sync_messages",
            ["entity_id"],
        )
        op.create_index(
            "ix_erp_sync_messages_status",
            "erp_sync_messages",
            ["status"],
        )
        op.create_index(
            "ix_erp_sync_messages_pick_list_id",
            "erp_sync_messages",
            ["pick_list_id"],
        )


def downgrade() -> None:
    if has_table("erp_sync_messages"):
        op.drop_index(
            "ix_erp_sync_messages_pick_list_id", table_name="erp_sync_messages"
        )
        op.drop_index(
            "ix_erp_sync_messages_status", table_name="erp_sync_messages"
        )
        op.drop_index(
            "ix_erp_sync_messages_entity_id", table_name="erp_sync_messages"
        )
        op.drop_index(
            "ix_erp_sync_messages_entity_type", table_name="erp_sync_messages"
        )
        op.drop_index(
            "ix_erp_sync_messages_organization_id", table_name="erp_sync_messages"
        )
        op.drop_table("erp_sync_messages")

    # PostgreSQL does not support dropping individual enum values.
