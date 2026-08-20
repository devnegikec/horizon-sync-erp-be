"""add_full_item_product_sync_columns

Revision ID: 076_add_full_item_product_sync_columns
Revises: 075_add_items_per_master_pack
Create Date: 2026-08-20

Adds the remaining mirror columns so Item and QRProduct can fully sync
metadata in both directions:

- Items gain the Product-native fields: generic_name, email, phone_number,
  banner_image_url, client_product_auth_url, redirect_to_client, is_active.
- QR products gain the Item-native fields: item_type, valuation_method,
  allow_negative_stock, item_group_id, variants, batch/serial series,
  reorder settings, inspection, tax templates, images, tags, custom_fields.

All new columns are nullable mirrors (no FK constraints) to keep the two
tables independently migratable.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.alembic_guards import has_column

# revision identifiers, used by Alembic.
revision: str = "076_add_full_item_product_sync_columns"
down_revision: Union[str, None] = "075_add_items_per_master_pack"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add(table: str, column: str, col: sa.Column) -> None:
    if not has_column(table, column):
        op.add_column(table, col)


def upgrade() -> None:
    # ── Items: add remaining Product-native columns ──
    _add("items", "generic_name", sa.Column("generic_name", sa.String(100), nullable=True))
    _add("items", "email", sa.Column("email", sa.String(255), nullable=True))
    _add("items", "phone_number", sa.Column("phone_number", sa.String(15), nullable=True))
    _add("items", "banner_image_url", sa.Column("banner_image_url", sa.Text(), nullable=True))
    _add("items", "client_product_auth_url", sa.Column("client_product_auth_url", sa.Text(), nullable=True))
    _add("items", "redirect_to_client", sa.Column("redirect_to_client", sa.Boolean(), nullable=True))
    _add("items", "is_active", sa.Column("is_active", sa.Boolean(), nullable=True))

    # ── QR products: add remaining Item-native columns ──
    _add("qr_products", "item_type", sa.Column("item_type", sa.String(50), nullable=True))
    _add("qr_products", "valuation_method", sa.Column("valuation_method", sa.String(50), nullable=True))
    _add("qr_products", "allow_negative_stock", sa.Column("allow_negative_stock", sa.Boolean(), nullable=True))
    _add("qr_products", "item_group_id", sa.Column("item_group_id", postgresql.UUID(as_uuid=True), nullable=True))
    _add("qr_products", "has_variants", sa.Column("has_variants", sa.Boolean(), nullable=True))
    _add("qr_products", "variant_of", sa.Column("variant_of", postgresql.UUID(as_uuid=True), nullable=True))
    _add("qr_products", "variant_attributes", sa.Column("variant_attributes", postgresql.JSONB(), nullable=True))
    _add("qr_products", "batch_number_series", sa.Column("batch_number_series", sa.String(100), nullable=True))
    _add("qr_products", "serial_number_series", sa.Column("serial_number_series", sa.String(100), nullable=True))
    _add("qr_products", "enable_auto_reorder", sa.Column("enable_auto_reorder", sa.Boolean(), nullable=True))
    _add("qr_products", "reorder_level", sa.Column("reorder_level", sa.Integer(), nullable=True))
    _add("qr_products", "reorder_qty", sa.Column("reorder_qty", sa.Integer(), nullable=True))
    _add("qr_products", "min_order_qty", sa.Column("min_order_qty", sa.Integer(), nullable=True))
    _add("qr_products", "max_order_qty", sa.Column("max_order_qty", sa.Integer(), nullable=True))
    _add("qr_products", "inspection_required_before_purchase", sa.Column("inspection_required_before_purchase", sa.Boolean(), nullable=True))
    _add("qr_products", "inspection_required_before_delivery", sa.Column("inspection_required_before_delivery", sa.Boolean(), nullable=True))
    _add("qr_products", "quality_inspection_template", sa.Column("quality_inspection_template", postgresql.UUID(as_uuid=True), nullable=True))
    _add("qr_products", "sales_tax_template_id", sa.Column("sales_tax_template_id", postgresql.UUID(as_uuid=True), nullable=True))
    _add("qr_products", "purchase_tax_template_id", sa.Column("purchase_tax_template_id", postgresql.UUID(as_uuid=True), nullable=True))
    _add("qr_products", "images", sa.Column("images", postgresql.JSONB(), nullable=True))
    _add("qr_products", "tags", sa.Column("tags", postgresql.JSONB(), nullable=True))
    _add("qr_products", "custom_fields", sa.Column("custom_fields", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "is_active")
    op.drop_column("items", "redirect_to_client")
    op.drop_column("items", "client_product_auth_url")
    op.drop_column("items", "banner_image_url")
    op.drop_column("items", "phone_number")
    op.drop_column("items", "email")
    op.drop_column("items", "generic_name")

    op.drop_column("qr_products", "custom_fields")
    op.drop_column("qr_products", "tags")
    op.drop_column("qr_products", "images")
    op.drop_column("qr_products", "purchase_tax_template_id")
    op.drop_column("qr_products", "sales_tax_template_id")
    op.drop_column("qr_products", "quality_inspection_template")
    op.drop_column("qr_products", "inspection_required_before_delivery")
    op.drop_column("qr_products", "inspection_required_before_purchase")
    op.drop_column("qr_products", "max_order_qty")
    op.drop_column("qr_products", "min_order_qty")
    op.drop_column("qr_products", "reorder_qty")
    op.drop_column("qr_products", "reorder_level")
    op.drop_column("qr_products", "enable_auto_reorder")
    op.drop_column("qr_products", "serial_number_series")
    op.drop_column("qr_products", "batch_number_series")
    op.drop_column("qr_products", "variant_attributes")
    op.drop_column("qr_products", "variant_of")
    op.drop_column("qr_products", "has_variants")
    op.drop_column("qr_products", "item_group_id")
    op.drop_column("qr_products", "allow_negative_stock")
    op.drop_column("qr_products", "valuation_method")
    op.drop_column("qr_products", "item_type")
