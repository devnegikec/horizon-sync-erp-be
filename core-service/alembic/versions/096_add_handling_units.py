"""Add handling_units table + pick_list_items.handling_unit_id

Revision ID: 096_add_handling_units
Revises: 095_add_pick_list_staging
Create Date: 2026-08-30

Adds the handling-unit (trolley/carton/pallet) table and links pick list items
to a handling unit (PR-11 / T-11, WF-018).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_table

revision: str = "096_add_handling_units"
down_revision: str | Sequence[str] | None = "095_add_pick_list_staging"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_table("handling_units"):
        op.create_table(
            "handling_units",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=True),
            sa.Column("hu_type", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["warehouse_id"], ["warehouses_extended.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint("organization_id", "code", name="uq_handling_units_org_code"),
        )
        op.create_index(
            "ix_handling_units_organization_id", "handling_units", ["organization_id"]
        )
        op.create_index(
            "ix_handling_units_warehouse_id", "handling_units", ["warehouse_id"]
        )
        op.create_index("ix_handling_units_hu_type", "handling_units", ["hu_type"])
        op.create_index("ix_handling_units_status", "handling_units", ["status"])

    if has_table("pick_list_items") and not has_column("pick_list_items", "handling_unit_id"):
        op.add_column(
            "pick_list_items",
            sa.Column("handling_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_pick_list_items_handling_unit_id",
            "pick_list_items",
            "handling_units",
            ["handling_unit_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if has_column("pick_list_items", "handling_unit_id"):
        op.drop_constraint(
            "fk_pick_list_items_handling_unit_id", "pick_list_items", type_="foreignkey"
        )
        op.drop_column("pick_list_items", "handling_unit_id")
    op.execute("DROP TABLE IF EXISTS handling_units")
