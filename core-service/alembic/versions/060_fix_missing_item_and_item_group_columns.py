"""fix missing columns on items and item_groups

Revision ID: 060_fix_missing_item_and_item_group_columns
Revises: 059_add_customer_unique_constraint
Create Date: 2026-06-08 14:00:00.000000

Migration 057 was supposed to reconcile the schema with models, but had a
bug where TypeDecorator types (e.g. our custom UUID) compiled to their
fallback impl (CHAR(32)) instead of the proper PostgreSQL type (UUID).
This left several columns missing on databases that were stamped past
057 without the schema actually being updated.

This migration explicitly adds the missing columns using Alembic
operations, which handle type compilation correctly.
"""
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "060_fix_missing_item_and_item_group_columns"
down_revision = "059_add_customer_unique_constraint"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(c["name"] == column_name for c in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    # ═════════════════════════════════════════════════════════════════
    # items
    # ═════════════════════════════════════════════════════════════════
    if inspector.has_table("items"):
        # ── sku ──
        if not _has_column(inspector, "items", "sku"):
            op.add_column("items", sa.Column("sku", sa.String(100), nullable=True))
            op.create_index("idx_items_sku", "items", ["sku"])

        # ── qr_product_id ──
        if not _has_column(inspector, "items", "qr_product_id"):
            op.add_column(
                "items",
                sa.Column(
                    "qr_product_id",
                    postgresql.UUID(as_uuid=True),
                    nullable=True,
                ),
            )
            op.create_index("ix_items_qr_product_id", "items", ["qr_product_id"])

            # Only add FK if qr_products table exists (created by 024 or 057)
            if inspector.has_table("qr_products"):
                op.create_foreign_key(
                    "fk_items_qr_product_id",
                    "items",
                    "qr_products",
                    ["qr_product_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

    # ═════════════════════════════════════════════════════════════════
    # item_groups
    # ═════════════════════════════════════════════════════════════════
    if inspector.has_table("item_groups"):
        # ── default_valuation_method ──
        if not _has_column(inspector, "item_groups", "default_valuation_method"):
            op.add_column(
                "item_groups",
                sa.Column(
                    "default_valuation_method",
                    postgresql.ENUM(
                        "fifo",
                        "lifo",
                        "moving_average",
                        "standard",
                        name="valuationmethod",
                        create_type=False,
                    ),
                    nullable=True,
                ),
            )

        # ── default_uom ──
        if not _has_column(inspector, "item_groups", "default_uom"):
            op.add_column(
                "item_groups",
                sa.Column("default_uom", sa.String(50), nullable=True),
            )

        # ── sales_tax_template_id ──
        if not _has_column(inspector, "item_groups", "sales_tax_template_id"):
            op.add_column(
                "item_groups",
                sa.Column(
                    "sales_tax_template_id",
                    postgresql.UUID(as_uuid=True),
                    nullable=True,
                ),
            )
            if inspector.has_table("tax_templates"):
                op.create_foreign_key(
                    "fk_item_groups_sales_tax_template",
                    "item_groups",
                    "tax_templates",
                    ["sales_tax_template_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

        # ── purchase_tax_template_id ──
        if not _has_column(inspector, "item_groups", "purchase_tax_template_id"):
            op.add_column(
                "item_groups",
                sa.Column(
                    "purchase_tax_template_id",
                    postgresql.UUID(as_uuid=True),
                    nullable=True,
                ),
            )
            if inspector.has_table("tax_templates"):
                op.create_foreign_key(
                    "fk_item_groups_purchase_tax_template",
                    "item_groups",
                    "tax_templates",
                    ["purchase_tax_template_id"],
                    ["id"],
                    ondelete="SET NULL",
                )


def downgrade() -> None:
    # No-op: forward-only fix. Dropping columns could destroy data.
    pass
