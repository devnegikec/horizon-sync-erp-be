"""Add notifications and warehouse_users tables

Revision ID: 051_add_notifications_and_warehouse_users
Revises: 050_add_asn_to_communication_doctype
Create Date: 2026-05-29

Creates:
  - notifications table for in-app WMS/ASN event notifications
  - warehouse_users table for role-based warehouse assignments
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "051_add_notifications_and_warehouse_users"
down_revision = "050_add_asn_to_communication_doctype"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notificationtype enum
    op.execute(
        "CREATE TYPE notificationtype AS ENUM ("
        "'asn_created', 'asn_confirmed', 'asn_cancelled', "
        "'fulfillment_initiated', 'fulfillment_completed', 'fulfillment_partially_completed', "
        "'receiving_slip_created', 'put_away_list_created', 'pick_list_created'"
        ")"
    )

    # Create warehouseuserrole enum
    op.execute(
        "CREATE TYPE warehouseuserrole AS ENUM ("
        "'supervisor', 'manager', 'operator', 'coordinator'"
        ")"
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "type",
            postgresql.ENUM(
                "asn_created", "asn_confirmed", "asn_cancelled",
                "fulfillment_initiated", "fulfillment_completed", "fulfillment_partially_completed",
                "receiving_slip_created", "put_away_list_created", "pick_list_created",
                name="notificationtype",
                create_type=False,
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True, index=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("entity_no", sa.String(100), nullable=True),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false", index=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
    )

    op.create_table(
        "warehouse_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
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
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("warehouse_users")
    op.drop_table("notifications")
    op.execute("DROP TYPE IF EXISTS warehouseuserrole")
    op.execute("DROP TYPE IF EXISTS notificationtype")
