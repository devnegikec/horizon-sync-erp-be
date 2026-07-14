"""Add bin_reservations table, bin_stock_levels.expiry_date, warehouse_locations.position_z

Revision ID: 059_add_bin_reservations_expiry_position_z
Revises: 058_add_employee_id_to_wms_workers
Create Date: 2026-06-16

Phase 1 foundation for the 3D Warehouse View & Smart Location Engine:
- bin_reservations: prevents two workers from being directed to the same bin
  simultaneously (concurrent worker coordination). A partial unique index keeps
  at most one active (un-released) reservation per bin; TTL expiry is enforced
  in the service layer (expires_at cannot be used in an index predicate as it
  is non-immutable).
- bin_stock_levels.expiry_date: enables FEFO (First Expired, First Out) picking.
- warehouse_locations.position_z: explicit Z-axis for 3D rendering, backfilled
  from each level's ordinal position within its bay.

Design ref: docs/3D_WAREHOUSE_VIEW_DESIGN.md sections 4.1, 4.2, 4.3
"""

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_index, has_table

revision = "059_add_bin_reservations_expiry_position_z"
down_revision = "058_add_employee_id_to_wms_workers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── bin_reservations ───────────────────────────────────────────
    if not has_table("bin_reservations"):
        conn.execute(
            sa.text(
                """
            CREATE TABLE bin_reservations (
                id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id     UUID NOT NULL,
                bin_location_id     UUID NOT NULL REFERENCES warehouse_locations(id),
                worker_id           UUID NOT NULL,
                task_id             UUID,
                task_type           VARCHAR(20),
                reserved_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
                expires_at          TIMESTAMPTZ NOT NULL,
                released_at         TIMESTAMPTZ,
                created_at          TIMESTAMPTZ DEFAULT now(),
                updated_at          TIMESTAMPTZ DEFAULT now()
            )
        """
            )
        )

    # At most one active (un-released) reservation per bin. TTL is enforced in
    # the service layer because NOW() is not immutable and cannot appear in an
    # index predicate.
    if not has_index("bin_reservations", "uq_active_bin_reservation"):
        conn.execute(
            sa.text(
                """
            CREATE UNIQUE INDEX uq_active_bin_reservation
            ON bin_reservations (bin_location_id)
            WHERE released_at IS NULL
        """
            )
        )

    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_bin_reservations_active "
        "ON bin_reservations (bin_location_id) WHERE released_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_bin_reservations_worker "
        "ON bin_reservations (worker_id, organization_id) WHERE released_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_bin_reservations_expires "
        "ON bin_reservations (expires_at) WHERE released_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_bin_reservations_org "
        "ON bin_reservations (organization_id)",
    ]:
        conn.execute(sa.text(idx_sql))

    # ── bin_stock_levels.expiry_date (FEFO) ────────────────────────
    if not has_column("bin_stock_levels", "expiry_date"):
        op.add_column(
            "bin_stock_levels",
            sa.Column("expiry_date", sa.Date(), nullable=True),
        )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_bin_stock_expiry "
            "ON bin_stock_levels (expiry_date) WHERE expiry_date IS NOT NULL"
        )
    )

    # ── warehouse_locations.position_z ─────────────────────────────
    if not has_column("warehouse_locations", "position_z"):
        op.add_column(
            "warehouse_locations",
            sa.Column(
                "position_z",
                sa.Numeric(10, 2),
                nullable=True,
                server_default="0",
            ),
        )

        # Backfill: level rows get a 0-based ordinal within their bay (ordered
        # by code); bins inherit their parent level's z. Other rows stay at 0.
        conn.execute(
            sa.text(
                """
            WITH level_z AS (
                SELECT
                    id,
                    (ROW_NUMBER() OVER (
                        PARTITION BY parent_location_id ORDER BY code
                    ) - 1) AS z
                FROM warehouse_locations
                WHERE location_type = 'level'
            )
            UPDATE warehouse_locations wl
            SET position_z = lz.z
            FROM level_z lz
            WHERE wl.id = lz.id
        """
            )
        )
        conn.execute(
            sa.text(
                """
            UPDATE warehouse_locations bin
            SET position_z = lvl.position_z
            FROM warehouse_locations lvl
            WHERE bin.location_type = 'bin'
              AND bin.parent_location_id = lvl.id
              AND lvl.location_type = 'level'
        """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()

    if has_column("warehouse_locations", "position_z"):
        op.drop_column("warehouse_locations", "position_z")

    conn.execute(sa.text("DROP INDEX IF EXISTS idx_bin_stock_expiry"))
    if has_column("bin_stock_levels", "expiry_date"):
        op.drop_column("bin_stock_levels", "expiry_date")

    if has_table("bin_reservations"):
        op.drop_table("bin_reservations")
