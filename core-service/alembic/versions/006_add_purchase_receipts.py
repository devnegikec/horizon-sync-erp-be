"""Add purchase receipts tables

Revision ID: 006_add_purchase_receipts
Revises: 005_add_landed_cost_vouchers
Create Date: 2026-02-15 10:30:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "006_add_purchase_receipts"
down_revision = "005_add_landed_cost_vouchers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create purchase_receipts table
    op.create_table(
        "purchase_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_receipt_no", sa.String(length=100), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "submitted",
                "cancelled",
                name="documentstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="purchase_receipts_supplier_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses_extended.id"],
            name="purchase_receipts_warehouse_id_fkey",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        op.f("ix_purchase_receipts_organization_id"),
        "purchase_receipts",
        ["organization_id"],
        unique=False,
    )

    # Create purchase_receipt_items table
    op.create_table(
        "purchase_receipt_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qty", sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column("uom", sa.String(length=50), nullable=False),
        sa.Column("rate", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("batch_no", sa.String(length=100), nullable=True),
        sa.Column("serial_nos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["purchase_receipt_id"],
            ["purchase_receipts.id"],
            name="purchase_receipt_items_purchase_receipt_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="purchase_receipt_items_item_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses_extended.id"],
            name="purchase_receipt_items_warehouse_id_fkey",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        op.f("ix_purchase_receipt_items_organization_id"),
        "purchase_receipt_items",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_purchase_receipt_items_organization_id"),
        table_name="purchase_receipt_items",
    )
    op.drop_table("purchase_receipt_items")
    op.drop_index(
        op.f("ix_purchase_receipts_organization_id"), table_name="purchase_receipts"
    )
    op.drop_table("purchase_receipts")
