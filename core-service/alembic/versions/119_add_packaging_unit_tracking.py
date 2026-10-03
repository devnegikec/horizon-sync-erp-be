"""Add packaging_unit_id to put_away_list_items and receiving_slip_items.

Carries the packaging unit (IC/MC) chosen at receiving through put-away so the
volumetric capacity engine can use master-carton outer dimensions instead of
always falling back to the base-unit (Each) dimensions.

Revision ID: 119_add_packaging_unit_tracking
Revises: 118_add_case_uom
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

from app.alembic_guards import has_column, has_index, has_table

revision: str = "119_add_packaging_unit_tracking"
down_revision: str | Sequence[str] | None = "118_add_case_uom"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── put_away_list_items.packaging_unit_id ──
    if has_table("put_away_list_items") and not has_column(
        "put_away_list_items", "packaging_unit_id"
    ):
        op.add_column(
            "put_away_list_items",
            sa.Column(
                "packaging_unit_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("item_packaging_units.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if has_table("put_away_list_items") and not has_index(
        "put_away_list_items", "ix_put_away_list_items_packaging_unit_id"
    ):
        op.create_index(
            "ix_put_away_list_items_packaging_unit_id",
            "put_away_list_items",
            ["packaging_unit_id"],
        )

    # ── receiving_slip_items.packaging_unit_id ──
    if has_table("receiving_slip_items") and not has_column(
        "receiving_slip_items", "packaging_unit_id"
    ):
        op.add_column(
            "receiving_slip_items",
            sa.Column(
                "packaging_unit_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("item_packaging_units.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if has_table("receiving_slip_items") and not has_index(
        "receiving_slip_items", "ix_receiving_slip_items_packaging_unit_id"
    ):
        op.create_index(
            "ix_receiving_slip_items_packaging_unit_id",
            "receiving_slip_items",
            ["packaging_unit_id"],
        )


def downgrade() -> None:
    if has_table("receiving_slip_items") and has_index(
        "receiving_slip_items", "ix_receiving_slip_items_packaging_unit_id"
    ):
        op.drop_index(
            "ix_receiving_slip_items_packaging_unit_id",
            table_name="receiving_slip_items",
        )
    if has_column("receiving_slip_items", "packaging_unit_id"):
        op.drop_column("receiving_slip_items", "packaging_unit_id")

    if has_table("put_away_list_items") and has_index(
        "put_away_list_items", "ix_put_away_list_items_packaging_unit_id"
    ):
        op.drop_index(
            "ix_put_away_list_items_packaging_unit_id",
            table_name="put_away_list_items",
        )
    if has_column("put_away_list_items", "packaging_unit_id"):
        op.drop_column("put_away_list_items", "packaging_unit_id")
