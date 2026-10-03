"""Add the model-required SKU column to QR products.

Revision ID: 048_add_qr_products_sku
Revises: 047_global_item_serial
Create Date: 2026-08-11
"""

import sqlalchemy as sa

from alembic import op

revision = "048_add_qr_products_sku"
down_revision = "047_global_item_serial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("qr_products")
    }
    if "sku" not in columns:
        op.add_column(
            "qr_products",
            sa.Column("sku", sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("qr_products")
    }
    if "sku" in columns:
        op.drop_column("qr_products", "sku")
