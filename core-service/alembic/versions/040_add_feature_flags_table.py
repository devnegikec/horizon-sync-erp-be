"""add feature_flags table for runtime feature toggling

Revision ID: 040_add_feature_flags_table
Revises: 039_add_audit_logs_table
Create Date: 2026-04-01 10:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "040_add_feature_flags_table"
down_revision = "039_add_audit_logs_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Always drop and recreate to handle schema mismatches
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    conn = op.get_bind()
    conn.execute(sa.text("DROP TABLE IF EXISTS feature_flags CASCADE"))

    op.create_table(
        "feature_flags",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "visible", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "scope",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'GLOBAL'"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "rollout_percentage",
            sa.Integer(),
            sa.CheckConstraint(
                "rollout_percentage >= 0 AND rollout_percentage <= 100",
                name="ck_feature_flags_rollout_pct",
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "name", "scope", "tenant_id", "user_id", name="uq_feature_flag_scope"
        ),
    )

    # Indexes for fast lookups
    op.create_index("ix_feature_flags_name", "feature_flags", ["name"])
    op.create_index("ix_feature_flags_scope", "feature_flags", ["scope"])

    # Idempotent check: if table existed before without 'visible', add it
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'feature_flags' AND column_name = 'visible'"
        )
    )
    if result.fetchone() is None:
        op.add_column(
            "feature_flags",
            sa.Column(
                "visible",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )


def downgrade() -> None:
    op.drop_index("ix_feature_flags_scope", table_name="feature_flags")
    op.drop_index("ix_feature_flags_name", table_name="feature_flags")
    op.drop_table("feature_flags")
