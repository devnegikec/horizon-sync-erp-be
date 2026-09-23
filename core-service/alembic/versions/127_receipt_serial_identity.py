"""Receipt serial identity: serial_nos on slip items + product_item_id FKs.

Phase 1 of the dispatch-slip serial-match work:

* ``receiving_slip_items.serial_nos`` (JSONB) — the document of record carries
  the unit serials it received (T1.1).
* ``product_item_id`` (UUID, nullable) on ``pick_list_items``,
  ``packing_slip_items``, ``asn_order_serial_lines``, ``scan_session_items`` and
  ``scanned_item_tracking`` — unit identity as a real key (T1.3).

The columns are backfilled from ``product_items.serial_number`` where the
matching key is unambiguous:

* ``asn_order_serial_lines`` / ``scan_session_items`` /
  ``scanned_item_tracking`` backfill by ``serial_no`` / ``qr_identifier``.
* ``pick_list_items`` / ``packing_slip_items`` backfill by the serials stored in
  their JSONB ``serial_nos`` array (first match wins for multi-serial lines).

All operations are idempotent (``has_table`` / ``has_column`` guards). Columns
are added as plain UUIDs (no DB-level FK) following the repo's "plain UUIDs"
pattern — the SQLAlchemy ``ForeignKey`` in the models governs fresh
``create_all`` databases.

Revision ID: 127_receipt_serial_identity
Revises: 126_dispatch_serial_match
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_table

revision: str = "127_receipt_serial_identity"
down_revision: str | Sequence[str] | None = "126_dispatch_serial_match"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (table, column) additions — plain UUIDs, nullable, backfilled separately.
UUID_COLUMNS = (
    ("pick_list_items", "product_item_id"),
    ("packing_slip_items", "product_item_id"),
    ("asn_order_serial_lines", "product_item_id"),
    ("scan_session_items", "product_item_id"),
    ("scanned_item_tracking", "product_item_id"),
)

#: Backfill by a scalar identifier column (identifier = product_items.serial_number).
SCALAR_BACKFILLS = (
    ("asn_order_serial_lines", "serial_no"),
    ("scan_session_items", "qr_identifier"),
    ("scanned_item_tracking", "qr_identifier"),
)

#: Backfill by a JSONB array of serials.
ARRAY_BACKFILLS = (
    ("pick_list_items",),
    ("packing_slip_items",),
)


def _scalar_backfill_sql(table: str, id_column: str) -> str:
    return f"""
        UPDATE {table} t
           SET product_item_id = pi.id
          FROM product_items pi
         WHERE pi.organization_id = t.organization_id
           AND pi.serial_number = t.{id_column}
           AND t.product_item_id IS NULL
    """


def _array_backfill_sql(table: str) -> str:
    return f"""
        UPDATE {table} t
           SET product_item_id = pi.id
          FROM product_items pi
         WHERE pi.organization_id = t.organization_id
           AND t.serial_nos IS NOT NULL
           AND t.serial_nos <> '[]'::jsonb
           AND pi.serial_number IN (
                 SELECT jsonb_array_elements_text(t.serial_nos)
               )
           AND t.product_item_id IS NULL
    """


def upgrade() -> None:
    # ── T1.1: receiving_slip_items.serial_nos ──────────────────────────
    if has_table("receiving_slip_items") and not has_column(
        "receiving_slip_items", "serial_nos"
    ):
        op.add_column(
            "receiving_slip_items",
            sa.Column("serial_nos", postgresql.JSONB(), nullable=True),
        )

    # ── T1.3: product_item_id columns ──────────────────────────────────
    for table, column in UUID_COLUMNS:
        if has_table(table) and not has_column(table, column):
            op.add_column(
                table,
                sa.Column(column, postgresql.UUID(as_uuid=True), nullable=True),
            )

    # ── Backfill product_item_id ───────────────────────────────────────
    if has_table("product_items"):
        for table, id_column in SCALAR_BACKFILLS:
            if has_table(table) and has_column(table, "product_item_id"):
                op.execute(sa.text(_scalar_backfill_sql(table, id_column)))
        for (table,) in ARRAY_BACKFILLS:
            if (
                has_table(table)
                and has_column(table, "product_item_id")
                and has_column(table, "serial_nos")
            ):
                op.execute(sa.text(_array_backfill_sql(table)))


def downgrade() -> None:
    for table, column in UUID_COLUMNS:
        if has_table(table) and has_column(table, column):
            op.drop_column(table, column)

    if has_table("receiving_slip_items") and has_column(
        "receiving_slip_items", "serial_nos"
    ):
        op.drop_column("receiving_slip_items", "serial_nos")
