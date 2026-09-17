"""sync_item_product_add_missing_columns

Revision ID: 069_sync_item_product
Revises: 068_drop_old_flag_constraint
Create Date: 2026-08-12

Add columns synced between Item ↔ QRProduct for bidirectional sync.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.alembic_guards import has_column, has_constraint, has_index, has_table

# revision identifiers
revision: str = "069_sync_item_product"
down_revision: Union[str, None] = "068_drop_old_flag_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Items: add Product-sourced columns ──
    item_columns = (
        ("brand_id", postgresql.UUID(as_uuid=True)),
        ("gtin", sa.String(20)),
        ("industry", sa.String(100)),
        ("landing_page", sa.Text()),
        ("warranty_period_months", sa.Integer()),
        ("qr_type", sa.String(30)),
        ("activation_method", sa.String(4)),
        ("sr_number_type", sa.String(50)),
    )
    if has_table("items"):
        for name, column_type in item_columns:
            if not has_column("items", name):
                op.add_column("items", sa.Column(name, column_type, nullable=True))
        if (
            has_table("brands")
            and has_column("items", "brand_id")
            and not has_constraint("items", "fk_items_brand_id")
        ):
            op.create_foreign_key("fk_items_brand_id", "items", "brands", ["brand_id"], ["id"])
        if has_column("items", "brand_id") and not has_index("items", "ix_items_brand_id"):
            op.create_index("ix_items_brand_id", "items", ["brand_id"])

    # ── QR Products: add Item-sourced columns ──
    product_columns = (
        ("item_code", sa.String(100)),
        ("description", sa.Text()),
        ("uom", sa.String(50)),
        ("standard_rate", sa.Numeric(15, 2)),
        ("valuation_rate", sa.Numeric(15, 2)),
        ("weight_per_unit", sa.Numeric(10, 3)),
        ("weight_uom", sa.String(50)),
        ("barcode", sa.String(100)),
        ("maintain_stock", sa.Boolean()),
        ("has_batch_no", sa.Boolean()),
        ("has_serial_no", sa.Boolean()),
    )
    if has_table("qr_products"):
        for name, column_type in product_columns:
            if not has_column("qr_products", name):
                op.add_column("qr_products", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    # ── Items: drop Product-sourced columns ──
    op.drop_constraint("fk_items_brand_id", "items", type_="foreignkey")
    op.drop_index("ix_items_brand_id", "items")
    op.drop_column("items", "sr_number_type")
    op.drop_column("items", "activation_method")
    op.drop_column("items", "qr_type")
    op.drop_column("items", "warranty_period_months")
    op.drop_column("items", "landing_page")
    op.drop_column("items", "industry")
    op.drop_column("items", "gtin")
    op.drop_column("items", "brand_id")

    # ── QR Products: drop Item-sourced columns ──
    op.drop_column("qr_products", "has_serial_no")
    op.drop_column("qr_products", "has_batch_no")
    op.drop_column("qr_products", "maintain_stock")
    op.drop_column("qr_products", "barcode")
    op.drop_column("qr_products", "weight_uom")
    op.drop_column("qr_products", "weight_per_unit")
    op.drop_column("qr_products", "valuation_rate")
    op.drop_column("qr_products", "standard_rate")
    op.drop_column("qr_products", "uom")
    op.drop_column("qr_products", "description")
    op.drop_column("qr_products", "item_code")
