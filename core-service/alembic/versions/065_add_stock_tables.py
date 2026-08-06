"""Add stock management tables

Revision ID: 065_add_stock_tables
Revises: 064_merge_heads
Create Date: 2026-08-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "065_add_stock_tables"
down_revision: Union[str, None] = "064_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Stock entries
    op.create_table(
        "stock_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("stock_entry_no", sa.String(100), nullable=False, index=True),
        sa.Column("stock_entry_type", sa.String(50), nullable=False),
        sa.Column("from_warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="SET NULL"), nullable=True),
        sa.Column("posting_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posting_time", sa.String(10), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("remarks", sa.Text, nullable=True),
        sa.Column("total_value", sa.Numeric(15, 2), nullable=True),
        sa.Column("expense_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cost_center_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_backflush", sa.Boolean, nullable=True),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("extra_data", postgresql.JSONB, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Stock entry items
    op.create_table(
        "stock_entry_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("stock_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="SET NULL"), nullable=True),
        sa.Column("qty", sa.Numeric(15, 3), nullable=False),
        sa.Column("uom", sa.String(50), nullable=False),
        sa.Column("basic_rate", sa.Numeric(15, 2), nullable=True),
        sa.Column("basic_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("valuation_rate", sa.Numeric(15, 2), nullable=True),
        sa.Column("batch_no", sa.String(100), nullable=True),
        sa.Column("serial_nos", postgresql.JSONB, nullable=True),
        sa.Column("quality_inspection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("extra_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Stock movements
    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"), nullable=False),
        sa.Column("movement_type", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Stock reconciliations
    op.create_table(
        "stock_reconciliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("reconciliation_no", sa.String(100), nullable=False, index=True),
        sa.Column("purpose", sa.String(100), nullable=True),
        sa.Column("posting_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posting_time", sa.String(10), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("expense_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("difference_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("remarks", sa.Text, nullable=True),
        sa.Column("extra_data", postgresql.JSONB, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Stock reconciliation items
    op.create_table(
        "stock_reconciliation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("reconciliation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_reconciliations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"), nullable=False),
        sa.Column("current_qty", sa.Numeric(15, 3), nullable=True),
        sa.Column("qty", sa.Numeric(15, 3), nullable=False),
        sa.Column("qty_difference", sa.Numeric(15, 3), nullable=True),
        sa.Column("current_valuation_rate", sa.Numeric(15, 2), nullable=True),
        sa.Column("valuation_rate", sa.Numeric(15, 2), nullable=True),
        sa.Column("batch_no", sa.String(100), nullable=True),
        sa.Column("serial_nos", postgresql.JSONB, nullable=True),
        sa.Column("extra_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Stock levels
    op.create_table(
        "stock_levels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_on_hand", sa.Integer, nullable=True, server_default="0"),
        sa.Column("quantity_reserved", sa.Integer, nullable=True, server_default="0"),
        sa.Column("quantity_available", sa.Integer, nullable=True, server_default="0"),
        sa.Column("last_counted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_stock_levels_product_warehouse"),
    )

    # Batches
    op.create_table(
        "batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("batch_no", sa.String(100), nullable=False, index=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("manufacturing_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supplier_batch_no", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("extra_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("batches")
    op.drop_table("stock_levels")
    op.drop_table("stock_reconciliation_items")
    op.drop_table("stock_reconciliations")
    op.drop_table("stock_movements")
    op.drop_table("stock_entry_items")
    op.drop_table("stock_entries")
