"""add feature_flags table for runtime feature toggling

Revision ID: 040_add_feature_flags_table
Revises: 039_add_audit_logs_table
Create Date: 2026-04-01 10:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "040_add_feature_flags_table"
down_revision = "039_add_audit_logs_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table("feature_flags"):
        columns = {
            column["name"]
            for column in inspector.get_columns("feature_flags")
        }
        current_columns = {
            "id",
            "name",
            "description",
            "enabled",
            "visible",
            "scope",
            "tenant_id",
            "user_id",
            "rollout_percentage",
            "created_at",
            "updated_at",
        }
        # Do not destroy flags already stored using the current schema. This
        # matters when repairing a database whose Alembic version lags behind
        # objects that were created out of band.
        if current_columns.issubset(columns):
            return

    # The original organization-scoped feature_flags table is incompatible
    # with the current global flag model and cannot be queried by the service.
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
