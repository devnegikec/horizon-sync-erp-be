"""Add ASN orders and ASN order items tables

Revision ID: 048_add_asn_orders_table
Revises: a52be5b21cef
Create Date: 2026-05-28

Creates asn_orders and asn_order_items tables for the Advance Stock Notice
feature, allowing pre-notification of incoming stock transfers.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "049_add_asn_orders_table"
down_revision = "048_merge_multiple_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create asnorderstatus enum
    op.execute(
        "CREATE TYPE asnorderstatus AS ENUM ('draft', 'confirmed', 'partially_delivered', 'delivered', 'closed', 'cancelled')"
    )

    op.create_table(
        "asn_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("asn_order_no", sa.String(100), nullable=False, index=True),
        sa.Column("warehouse_id_from", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="SET NULL"), nullable=True),
        sa.Column("warehouse_id_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", postgresql.ENUM("draft", "confirmed", "partially_delivered", "delivered", "closed", "cancelled", name="asnorderstatus", create_type=False), nullable=False, server_default="draft"),
        sa.Column("grand_total", sa.Numeric(15, 3), nullable=False, server_default="0"),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_no", sa.String(100), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "asn_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("asn_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asn_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qty", sa.Numeric(15, 3), nullable=False),
        sa.Column("uom", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivered_qty", sa.Numeric(15, 3), nullable=False, server_default="0"),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("asn_order_items")
    op.drop_table("asn_orders")
    op.execute("DROP TYPE IF EXISTS asnorderstatus")
