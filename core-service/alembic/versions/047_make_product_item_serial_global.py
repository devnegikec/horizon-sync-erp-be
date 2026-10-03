"""Make active ProductItem serial numbers globally unique.

Revision ID: 047_global_item_serial
Revises: 046_qr_credit_reservations
Create Date: 2026-08-05
"""

import sqlalchemy as sa

from alembic import op

revision = "047_global_item_serial"
down_revision = "046_qr_credit_reservations"
branch_labels = None
depends_on = None


def _assert_no_active_duplicates() -> None:
    duplicate = op.get_bind().execute(
        sa.text(
            """
            SELECT serial_number
            FROM product_items
            WHERE deleted_at IS NULL
            GROUP BY serial_number
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate:
        raise RuntimeError(
            "Cannot make ProductItem serial numbers globally unique: active "
            f"duplicate serial '{duplicate[0]}' exists. Resolve duplicates "
            "before rerunning this migration."
        )


def upgrade() -> None:
    _assert_no_active_duplicates()
    op.drop_index(
        "uq_product_items_org_serial_active",
        table_name="product_items",
    )
    op.create_index(
        "uq_product_items_serial_active",
        "product_items",
        ["serial_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_product_items_serial_active",
        table_name="product_items",
    )
    op.create_index(
        "uq_product_items_org_serial_active",
        "product_items",
        ["organization_id", "serial_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
