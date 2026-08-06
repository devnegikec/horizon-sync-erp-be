"""Add Shelf Life setting reference to QR Products.

Revision ID: 040_add_product_shelf_life
Revises: 0167307b0bd5
Create Date: 2026-07-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "040_add_product_shelf_life"
down_revision = "0167307b0bd5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "qr_products",
        sa.Column(
            "shelf_life_setting_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_qr_products_shelf_life_setting_id",
        "qr_products",
        ["shelf_life_setting_id"],
    )
    op.create_foreign_key(
        "fk_qr_products_shelf_life_setting_id",
        "qr_products",
        "qr_product_settings",
        ["shelf_life_setting_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Preserve legacy Product form values when they match an organization-scoped
    # Shelf Life setting. Unmatched products intentionally remain NULL.
    op.execute(
        """
        UPDATE qr_products AS product
        SET shelf_life_setting_id = setting.id
        FROM qr_product_settings AS setting
        WHERE product.shelf_life_setting_id IS NULL
          AND product.warranty_period_months IS NOT NULL
          AND setting.organization_id = product.organization_id
          AND setting.setting_type = 'shelf_life'
          AND setting.value = product.warranty_period_months::text
          AND setting.deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_qr_products_shelf_life_setting_id",
        "qr_products",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_qr_products_shelf_life_setting_id",
        table_name="qr_products",
    )
    op.drop_column("qr_products", "shelf_life_setting_id")
