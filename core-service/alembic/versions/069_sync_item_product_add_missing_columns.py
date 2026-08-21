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

# revision identifiers
revision: str = "069_sync_item_product"
down_revision: Union[str, None] = "068_drop_old_flag_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Items: add Product-sourced columns ──
    op.add_column("items", sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("items", sa.Column("gtin", sa.String(20), nullable=True))
    op.add_column("items", sa.Column("industry", sa.String(100), nullable=True))
    op.add_column("items", sa.Column("landing_page", sa.Text(), nullable=True))
    op.add_column("items", sa.Column("warranty_period_months", sa.Integer(), nullable=True))
    op.add_column("items", sa.Column("qr_type", sa.String(30), nullable=True))
    op.add_column("items", sa.Column("activation_method", sa.String(4), nullable=True))
    op.add_column("items", sa.Column("sr_number_type", sa.String(50), nullable=True))
    op.create_foreign_key("fk_items_brand_id", "items", "brands", ["brand_id"], ["id"])
    op.create_index("ix_items_brand_id", "items", ["brand_id"])

    # ── QR Products: add Item-sourced columns ──
    op.add_column("qr_products", sa.Column("item_code", sa.String(100), nullable=True))
    op.add_column("qr_products", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("qr_products", sa.Column("uom", sa.String(50), nullable=True))
    op.add_column("qr_products", sa.Column("standard_rate", sa.Numeric(15, 2), nullable=True))
    op.add_column("qr_products", sa.Column("valuation_rate", sa.Numeric(15, 2), nullable=True))
    op.add_column("qr_products", sa.Column("weight_per_unit", sa.Numeric(10, 3), nullable=True))
    op.add_column("qr_products", sa.Column("weight_uom", sa.String(50), nullable=True))
    op.add_column("qr_products", sa.Column("barcode", sa.String(100), nullable=True))
    op.add_column("qr_products", sa.Column("maintain_stock", sa.Boolean(), nullable=True))
    op.add_column("qr_products", sa.Column("has_batch_no", sa.Boolean(), nullable=True))
    op.add_column("qr_products", sa.Column("has_serial_no", sa.Boolean(), nullable=True))


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
