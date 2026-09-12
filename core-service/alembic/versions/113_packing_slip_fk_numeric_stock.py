"""Add packing_slip_id FK and widen stock_levels quantities to Numeric.

The packing-slip dispatch feature added ``dispatch_records.packing_slip_id``
without a foreign key, and fractional packing-slip quantities were silently
truncated because ``stock_levels`` quantity columns were integers. Add the FK
and widen the summary stock columns to Numeric(15, 3) to match the Numeric
precision used by bin_stock_levels and packing_slip_items.

This migration reconciles databases that already ran
``112_dispatch_from_packing_slip`` (which added the column without the FK).

Revision ID: 113_packing_slip_fk_numeric_stock
Revises: ddd66635a953
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "113_packing_slip_fk_numeric_stock"
down_revision: str | Sequence[str] | None = "ddd66635a953"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_QUANTITY_COLUMNS = ("quantity_on_hand", "quantity_reserved", "quantity_available")


def _fk_exists(conn, table: str, constraint: str) -> bool:
    return (
        conn.execute(
            sa.text(
                "SELECT 1 FROM pg_constraint "
                "WHERE conname = :name AND conrelid = to_regclass(:table)"
            ),
            {"name": constraint, "table": table},
        ).scalar()
        is not None
    )


def upgrade() -> None:
    conn = op.get_bind()

    if not _fk_exists(
        conn, "dispatch_records", "dispatch_records_packing_slip_id_fkey"
    ):
        op.create_foreign_key(
            "dispatch_records_packing_slip_id_fkey",
            "dispatch_records",
            "packing_slips",
            ["packing_slip_id"],
            ["id"],
        )

    for column in _QUANTITY_COLUMNS:
        op.execute(
            f"ALTER TABLE stock_levels "
            f"ALTER COLUMN {column} TYPE numeric(15, 3) "
            f"USING {column}::numeric(15, 3)"
        )


def downgrade() -> None:
    for column in _QUANTITY_COLUMNS:
        # Narrowing back to integer would silently drop fractional quantities.
        # Fail loudly when fractional data exists instead of corrupting totals.
        op.execute(
            "DO $$ "
            "BEGIN "
            "IF EXISTS ("
            "  SELECT 1 FROM stock_levels "
            f"  WHERE {column} IS NOT NULL AND {column} <> ROUND({column})"
            ") THEN "
            "RAISE EXCEPTION 'downgrade would lose fractional stock quantities'; "
            "END IF; "
            "END $$;"
        )
        op.execute(
            f"ALTER TABLE stock_levels "
            f"ALTER COLUMN {column} TYPE integer "
            f"USING {column}::integer"
        )

    conn = op.get_bind()
    if _fk_exists(
        conn, "dispatch_records", "dispatch_records_packing_slip_id_fkey"
    ):
        op.drop_constraint(
            "dispatch_records_packing_slip_id_fkey",
            "dispatch_records",
            type_="foreignkey",
        )
