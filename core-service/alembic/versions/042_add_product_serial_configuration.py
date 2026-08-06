"""Add Product-owned serial-prefix configuration and normalize serial types.

Revision ID: 042_product_serial_config
Revises: 041_qr_block_integrity
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "042_product_serial_config"
down_revision = "041_qr_block_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "qr_products",
        sa.Column(
            "serial_prefix_setting_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_qr_products_serial_prefix_setting_id",
        "qr_products",
        ["serial_prefix_setting_id"],
    )
    op.create_foreign_key(
        "fk_qr_products_serial_prefix_setting_id",
        "qr_products",
        "qr_product_settings",
        ["serial_prefix_setting_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Normalize legacy Product form values to the generation contract. Prefixes
    # are intentionally not backfilled because the correct setting cannot be
    # inferred safely from existing Product records.
    op.execute(
        """
        UPDATE qr_products
        SET sr_number_type = CASE lower(sr_number_type)
            WHEN 'random_8_alpha_numeric' THEN 'R8DAN'
            WHEN 'random_6_alpha_numeric' THEN 'R6DAN'
            WHEN 'random_4_alpha_numeric' THEN 'R4DAN'
            WHEN 'sequential' THEN 'S8DN'
            WHEN 'sequential_8_digit' THEN 'S8DN'
            WHEN 'sequential_10_digit' THEN 'S10DN'
            ELSE sr_number_type
        END
        WHERE sr_number_type IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE qr_products
        SET sr_number_type = CASE upper(sr_number_type)
            WHEN 'R8DAN' THEN 'random_8_alpha_numeric'
            WHEN 'R6DAN' THEN 'random_6_alpha_numeric'
            WHEN 'R4DAN' THEN 'random_4_alpha_numeric'
            WHEN 'S8DN' THEN 'sequential'
            ELSE sr_number_type
        END
        WHERE sr_number_type IS NOT NULL
        """
    )
    op.drop_constraint(
        "fk_qr_products_serial_prefix_setting_id",
        "qr_products",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_qr_products_serial_prefix_setting_id",
        table_name="qr_products",
    )
    op.drop_column("qr_products", "serial_prefix_setting_id")
