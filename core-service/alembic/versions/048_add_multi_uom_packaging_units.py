"""Add multi-UOM packaging units: item_packaging_units table, sku on items,
   volumetric capacity on warehouse_locations, packaging_unit_id on
   bin_stock_levels and scan_session_items, rename quantity→raw_quantity.

Revision ID: 048_add_multi_uom_packaging_units
Revises: a52be5b21cef
Create Date: 2025-07-15

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "048_add_multi_uom_packaging_units"
down_revision = "a52be5b21cef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ══════════════════════════════════════════════════════════════════
    # 1. Create item_packaging_units
    #    (must come first — other tables FK to it)
    # ══════════════════════════════════════════════════════════════════
    op.create_table(
        "item_packaging_units",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("unit_name", sa.String(100), nullable=False),
        sa.Column("qr_identifier", sa.String(255), nullable=True),
        sa.Column("conversion_factor", sa.Numeric(15, 6), nullable=False),
        sa.Column("length_mm", sa.Numeric(10, 2), nullable=True),
        sa.Column("width_mm", sa.Numeric(10, 2), nullable=True),
        sa.Column("height_mm", sa.Numeric(10, 2), nullable=True),
        sa.Column("weight_grams", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "is_base_unit",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("item_id", "unit_name", name="uq_item_unit_name"),
        sa.CheckConstraint(
            "conversion_factor > 0",
            name="chk_conversion_factor_positive",
        ),
    )

    # Indexes for item_packaging_units
    op.create_index("idx_ipu_org", "item_packaging_units", ["organization_id"])
    op.create_index("idx_ipu_item_id", "item_packaging_units", ["item_id"])
    op.create_index(
        "idx_ipu_qr_identifier",
        "item_packaging_units",
        ["qr_identifier"],
        unique=True,
        postgresql_where=sa.text("qr_identifier IS NOT NULL"),
    )

    # ══════════════════════════════════════════════════════════════════
    # 2. Add sku column to items
    # ══════════════════════════════════════════════════════════════════
    op.add_column(
        "items",
        sa.Column("sku", sa.String(100), nullable=True),
    )
    op.create_index("idx_items_sku", "items", ["sku"])

    # ══════════════════════════════════════════════════════════════════
    # 3. Add packaging_unit_id to bin_stock_levels
    # ══════════════════════════════════════════════════════════════════
    op.add_column(
        "bin_stock_levels",
        sa.Column(
            "packaging_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("item_packaging_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ══════════════════════════════════════════════════════════════════
    # 4. Add volumetric capacity columns to warehouse_locations
    # ══════════════════════════════════════════════════════════════════
    op.add_column(
        "warehouse_locations",
        sa.Column("max_volume_cc", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "warehouse_locations",
        sa.Column("max_weight_grams", sa.Numeric(15, 2), nullable=True),
    )

    # ══════════════════════════════════════════════════════════════════
    # 5. Rename quantity → raw_quantity on scan_session_items
    # ══════════════════════════════════════════════════════════════════
    op.alter_column(
        "scan_session_items",
        "quantity",
        new_column_name="raw_quantity",
    )

    # ══════════════════════════════════════════════════════════════════
    # 6. Add packaging_unit_id to scan_session_items
    # ══════════════════════════════════════════════════════════════════
    op.add_column(
        "scan_session_items",
        sa.Column(
            "packaging_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("item_packaging_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Reverse in strict reverse order:
    # drop FK columns first, then drop the referenced item_packaging_units table.

    # ── 6. Drop packaging_unit_id from scan_session_items ──
    op.drop_column("scan_session_items", "packaging_unit_id")

    # ── 5. Rename raw_quantity → quantity on scan_session_items ──
    op.alter_column(
        "scan_session_items",
        "raw_quantity",
        new_column_name="quantity",
    )

    # ── 4. Drop volumetric capacity columns from warehouse_locations ──
    op.drop_column("warehouse_locations", "max_weight_grams")
    op.drop_column("warehouse_locations", "max_volume_cc")

    # ── 3. Drop packaging_unit_id from bin_stock_levels ──
    op.drop_column("bin_stock_levels", "packaging_unit_id")

    # ── 2. Drop sku index and column from items ──
    op.drop_index("idx_items_sku", table_name="items")
    op.drop_column("items", "sku")

    # ── 1. Drop item_packaging_units indexes and table ──
    op.drop_index("idx_ipu_qr_identifier", table_name="item_packaging_units")
    op.drop_index("idx_ipu_item_id", table_name="item_packaging_units")
    op.drop_index("idx_ipu_org", table_name="item_packaging_units")
    op.drop_table("item_packaging_units")
