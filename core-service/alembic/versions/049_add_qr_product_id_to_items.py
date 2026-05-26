"""add qr_product_id to items

Revision ID: 049_add_qr_product_id_to_items
Revises: 048_add_multi_uom_packaging_units
Create Date: 2026-05-25

Links each inventory Item to an optional QRProduct, enabling unit-level
QR code tracking. The relationship is many-to-one: multiple items can
reference the same QR product profile, but each item has at most one.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "049_add_qr_product_id_to_items"
down_revision = "048_add_multi_uom_packaging_units"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add qr_product_id FK column to items
    op.add_column(
        "items",
        sa.Column(
            "qr_product_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # Index for fast lookups: "which items use this QR product?"
    op.create_index(
        "ix_items_qr_product_id",
        "items",
        ["qr_product_id"],
    )

    # Foreign key constraint
    op.create_foreign_key(
        "fk_items_qr_product_id",
        "items",
        "qr_products",
        ["qr_product_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_items_qr_product_id", "items", type_="foreignkey")
    op.drop_index("ix_items_qr_product_id", table_name="items")
    op.drop_column("items", "qr_product_id")
