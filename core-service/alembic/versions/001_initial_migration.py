"""Initial migration for Core Service

Revision ID: 001
Revises:
Create Date: 2026-01-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create item_groups table
    op.create_table(
        "item_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "parent_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
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
        sa.Column("default_uom", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_item_groups_code"), "item_groups", ["code"], unique=False
    )
    op.create_index(
        op.f("ix_item_groups_organization_id"),
        "item_groups",
        ["organization_id"],
        unique=False,
    )
    op.create_foreign_key(
        "item_groups_parent_id_fkey",
        "item_groups",
        "item_groups",
        ["parent_id"],
        ["id"],
    )

    # Create items table
    op.create_table(
        "items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_code", sa.String(length=100), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("item_group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "item_type",
            postgresql.ENUM(
                "stock",
                "non_stock",
                "service",
                "fixed_asset",
                name="itemtype",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("uom", sa.String(length=50), nullable=True),
        sa.Column("maintain_stock", sa.Boolean(), nullable=True),
        sa.Column(
            "valuation_method",
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
        sa.Column("allow_negative_stock", sa.Boolean(), nullable=True),
        sa.Column("has_variants", sa.Boolean(), nullable=True),
        sa.Column("variant_of", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("variant_attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("has_batch_no", sa.Boolean(), nullable=True),
        sa.Column("has_serial_no", sa.Boolean(), nullable=True),
        sa.Column("batch_number_series", sa.String(length=100), nullable=True),
        sa.Column("serial_number_series", sa.String(length=100), nullable=True),
        sa.Column("standard_rate", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("valuation_rate", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("enable_auto_reorder", sa.Boolean(), nullable=True),
        sa.Column("reorder_level", sa.Integer(), nullable=True),
        sa.Column("reorder_qty", sa.Integer(), nullable=True),
        sa.Column("min_order_qty", sa.Integer(), nullable=True),
        sa.Column("max_order_qty", sa.Integer(), nullable=True),
        sa.Column("weight_per_unit", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("weight_uom", sa.String(length=50), nullable=True),
        sa.Column("inspection_required_before_purchase", sa.Boolean(), nullable=True),
        sa.Column("inspection_required_before_delivery", sa.Boolean(), nullable=True),
        sa.Column("quality_inspection_template", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("barcode", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active",
                "inactive",
                "discontinued",
                name="itemstatus",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("images", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_items_item_code"), "items", ["item_code"], unique=False)
    op.create_index(
        op.f("ix_items_organization_id"), "items", ["organization_id"], unique=False
    )
    op.create_foreign_key(
        "items_item_group_id_fkey", "items", "item_groups", ["item_group_id"], ["id"]
    )
    op.create_foreign_key(
        "items_variant_of_fkey", "items", "items", ["variant_of"], ["id"]
    )

    # Create warehouses_extended table
    op.create_table(
        "warehouses_extended",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "warehouse_type",
            postgresql.ENUM(
                "warehouse",
                "store",
                "virtual",
                "transit",
                name="warehousetype",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("address_line1", sa.String(length=255), nullable=True),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("total_capacity", sa.Integer(), nullable=True),
        sa.Column("capacity_uom", sa.String(length=50), nullable=True),
        sa.Column("stock_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_warehouses_extended_code"),
        "warehouses_extended",
        ["code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_warehouses_extended_organization_id"),
        "warehouses_extended",
        ["organization_id"],
        unique=False,
    )
    op.create_foreign_key(
        "warehouses_extended_parent_warehouse_id_fkey",
        "warehouses_extended",
        "warehouses_extended",
        ["parent_warehouse_id"],
        ["id"],
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("warehouses_extended")
    op.drop_table("items")
    op.drop_table("item_groups")
