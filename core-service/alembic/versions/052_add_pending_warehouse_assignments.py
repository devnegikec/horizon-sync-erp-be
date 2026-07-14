"""Add pending_warehouse_assignments table

Revision ID: 052_add_pending_warehouse_assignments
Revises: 051_add_notifications_and_warehouse_users
Create Date: 2026-05-30

Creates pending_warehouse_assignments table for storing warehouse
assignments keyed by email before the invited user accepts.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table

# revision identifiers, used by Alembic.
revision = "052_add_pending_warehouse_assignments"
down_revision = "051_add_notifications_and_warehouse_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not has_table("pending_warehouse_assignments"):
        op.create_table(
            "pending_warehouse_assignments",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("email", sa.String(255), nullable=False, index=True),
            sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "role",
                postgresql.ENUM(
                    "supervisor", "manager", "operator", "coordinator",
                    name="warehouseuserrole",
                    create_type=False,
                ),
                nullable=False,
                server_default="operator",
            ),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )


def downgrade() -> None:
    if has_table("pending_warehouse_assignments"):
        op.drop_table("pending_warehouse_assignments")
