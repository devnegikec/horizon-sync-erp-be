"""Add packaging_types master and link item_packaging_units.

Revision ID: 079_packaging_types
Revises: 078_uom_fks

Creates the reusable ``packaging_types`` master (Case, Pallet, Drum…) and adds
``item_packaging_units.packaging_type_id`` as an optional FK. Data seeding of
packaging types from existing ``unit_name`` values happens in a separate seed
script (P0-7), not in this migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.alembic_guards import has_column, has_constraint, has_index, has_table

revision: str = "079_packaging_types"
down_revision: str | Sequence[str] | None = "078_uom_fks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_table("packaging_types"):
        op.create_table(
            "packaging_types",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("uom_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("length_mm", sa.Numeric(10, 2), nullable=True),
            sa.Column("width_mm", sa.Numeric(10, 2), nullable=True),
            sa.Column("height_mm", sa.Numeric(10, 2), nullable=True),
            sa.Column("weight_grams", sa.Numeric(10, 2), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        if not has_index("packaging_types", "ix_packaging_types_organization_id"):
            op.create_index("ix_packaging_types_organization_id", "packaging_types", ["organization_id"])
        if not has_index("packaging_types", "ix_packaging_types_code"):
            op.create_index("ix_packaging_types_code", "packaging_types", ["code"])
        if not has_constraint("packaging_types", "fk_packaging_types_uom_id_uoms"):
            op.create_foreign_key(
                "fk_packaging_types_uom_id_uoms", "packaging_types", "uoms", ["uom_id"], ["id"]
            )

    if not has_column("item_packaging_units", "packaging_type_id"):
        op.add_column(
            "item_packaging_units",
            sa.Column("packaging_type_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if not has_index("item_packaging_units", "ix_item_packaging_units_packaging_type_id"):
        op.create_index(
            "ix_item_packaging_units_packaging_type_id",
            "item_packaging_units",
            ["packaging_type_id"],
        )
    if not has_constraint("item_packaging_units", "fk_item_packaging_units_packaging_type_id"):
        op.create_foreign_key(
            "fk_item_packaging_units_packaging_type_id",
            "item_packaging_units",
            "packaging_types",
            ["packaging_type_id"],
            ["id"],
        )


def downgrade() -> None:
    if has_constraint("item_packaging_units", "fk_item_packaging_units_packaging_type_id"):
        op.drop_constraint("fk_item_packaging_units_packaging_type_id", "item_packaging_units", type_="foreignkey")
    if has_column("item_packaging_units", "packaging_type_id"):
        op.drop_index("ix_item_packaging_units_packaging_type_id", table_name="item_packaging_units")
        op.drop_column("item_packaging_units", "packaging_type_id")
    if has_table("packaging_types"):
        op.drop_constraint("fk_packaging_types_uom_id_uoms", "packaging_types", type_="foreignkey")
        op.drop_table("packaging_types")
