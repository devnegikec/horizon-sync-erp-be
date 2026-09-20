"""Backfill ``bin_stock_levels.inventory_status`` for segregated stock.

G-D1 / E-05: stock physically parked in a segregation system bin (HOLD,
QUARANTINE, DAMAGED) was recorded with the column default ``available``, so
status-based reporting/analytics counted damaged, held or quarantined units as
sellable even though the bin itself is non-pickable. The service now sets the
status when it segregates stock; this migration repairs the rows created before
that change.

Mapping (mirrors ``InboundExceptionService.DESTINATION_INVENTORY_STATUS``):

| system bin | inventory_status |
| ---------- | ---------------- |
| ``HOLD``       | ``hold``    |
| ``QUARANTINE`` | ``quality`` |
| ``DAMAGED``    | ``damaged`` |

Revision ID: 121_backfill_segregated_stock_status
Revises: 120_fix_shortage_history_fk
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "121_backfill_segregated_stock_status"
down_revision: str | Sequence[str] | None = "120_fix_shortage_history_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Supports the scan-time duplicate-identity hard stop (G-E3 / E-13), which
#: looks an identity up by (organization, batch/identity).
IDENTITY_INDEX = "ix_bin_stock_levels_org_batch"

#: system bin code → ``bin_stock_levels.inventory_status``
BIN_STATUS = (
    ("HOLD", "hold"),
    ("QUARANTINE", "quality"),
    ("DAMAGED", "damaged"),
)

_UPDATE = sa.text(
    """
    UPDATE bin_stock_levels AS bsl
       SET inventory_status = :status,
           updated_at = now()
      FROM warehouse_locations AS wl
     WHERE bsl.bin_location_id = wl.id
       AND wl.code = :bin_code
       AND bsl.quantity_on_hand > 0
       AND bsl.inventory_status = :from_status
    """
)


def upgrade() -> None:
    if not has_table("bin_stock_levels") or not has_table("warehouse_locations"):
        return

    if not has_index("bin_stock_levels", IDENTITY_INDEX):
        op.create_index(
            IDENTITY_INDEX,
            "bin_stock_levels",
            ["organization_id", "batch_number"],
        )

    for bin_code, status in BIN_STATUS:
        op.execute(
            _UPDATE.bindparams(
                bin_code=bin_code, status=status, from_status="available"
            )
        )


def downgrade() -> None:
    """Drop the supporting index; the backfilled statuses deliberately stay.

    The upgrade repaired rows whose ``inventory_status`` was already wrong
    (``available`` inside a segregation bin). Those rows carry no marker, and
    the application legitimately writes the same ``hold`` / ``quality`` /
    ``damaged`` values when it segregates stock, so a rollback cannot tell a
    repaired row from one the application has since set. Resetting them all to
    ``available`` would re-create the original defect for every row segregated
    after this migration ran, so it is intentionally not attempted.
    """
    if not has_table("bin_stock_levels") or not has_table("warehouse_locations"):
        return

    if has_index("bin_stock_levels", IDENTITY_INDEX):
        op.drop_index(IDENTITY_INDEX, "bin_stock_levels")
