"""Add admin portal tables: user_activity_logs, admin_audit_logs, admin_notifications, feature_flags

Revision ID: 034_add_admin_portal_tables
Revises: 033_add_qr_product_settings
Create Date: 2026-03-22 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "034_add_admin_portal_tables"
down_revision = "033_add_qr_product_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── user_activity_logs ──
    op.create_table(
        "user_activity_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    # user_activity_logs indexes
    op.create_index(
        "idx_activity_logs_user", "user_activity_logs", ["user_id"]
    )
    op.create_index(
        "idx_activity_logs_org", "user_activity_logs", ["organization_id"]
    )
    op.create_index(
        "idx_activity_logs_action", "user_activity_logs", ["action"]
    )
    op.create_index(
        "idx_activity_logs_created", "user_activity_logs", ["created_at"]
    )

    # ── admin_audit_logs ──
    op.create_table(
        "admin_audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "admin_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changes", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    # admin_audit_logs indexes
    op.create_index(
        "idx_audit_logs_admin", "admin_audit_logs", ["admin_user_id"]
    )
    op.create_index(
        "idx_audit_logs_target",
        "admin_audit_logs",
        ["target_type", "target_id"],
    )
    op.create_index(
        "idx_audit_logs_created", "admin_audit_logs", ["created_at"]
    )

    # ── admin_notifications ──
    op.create_table(
        "admin_notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "recipient_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_read", sa.Boolean, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    # admin_notifications indexes
    op.create_index(
        "idx_notifications_recipient",
        "admin_notifications",
        ["recipient_user_id"],
    )
    op.create_index(
        "idx_notifications_unread",
        "admin_notifications",
        ["recipient_user_id", "is_read"],
        postgresql_where=sa.text("is_read = FALSE"),
    )
    op.create_index(
        "idx_notifications_created", "admin_notifications", ["created_at"]
    )

    # ── feature_flags ──
    op.create_table(
        "feature_flags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("feature_key", sa.String(100), nullable=False),
        sa.Column("is_enabled", sa.Boolean, server_default="false"),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    # feature_flags indexes and constraints
    op.create_index(
        "idx_feature_flags_org", "feature_flags", ["organization_id"]
    )
    op.create_unique_constraint(
        "unique_org_feature",
        "feature_flags",
        ["organization_id", "feature_key"],
    )


def downgrade() -> None:
    op.drop_table("feature_flags")
    op.drop_table("admin_notifications")
    op.drop_table("admin_audit_logs")
    op.drop_table("user_activity_logs")
