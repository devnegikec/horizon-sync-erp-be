"""Add bin_stock_levels and location_allocations tables

Revision ID: 043_add_bin_stock_levels_and_location_allocations
Revises: 042_add_warehouse_locations
Create Date: 2025-07-14

Creates the bin_stock_levels table for tracking stock at individual bin
locations, and the location_allocations table for linking locations to
item groups (exclusive/preferred allocation for put-away prioritization).

Requirements: 3.1, 20.1, 20.2
"""

from alembic import op
import sqlalchemy as sa

revision = '043_add_bin_stock_levels_and_location_allocations'
down_revision = '042_add_warehouse_locations_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── bin_stock_levels ───────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS bin_stock_levels (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id     UUID NOT NULL,
            bin_location_id     UUID NOT NULL REFERENCES warehouse_locations(id),
            item_id             UUID NOT NULL REFERENCES items(id),
            quantity_on_hand    NUMERIC(15, 3) DEFAULT 0,
            batch_number        VARCHAR(100),
            created_at          TIMESTAMPTZ DEFAULT now(),
            updated_at          TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_bin_item_batch UNIQUE (bin_location_id, item_id, batch_number)
        )
    """))

    # Indexes for bin_stock_levels
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_bsl_org ON bin_stock_levels(organization_id)",
        "CREATE INDEX IF NOT EXISTS idx_bsl_bin ON bin_stock_levels(bin_location_id)",
        "CREATE INDEX IF NOT EXISTS idx_bsl_item ON bin_stock_levels(item_id)",
        "CREATE INDEX IF NOT EXISTS idx_bsl_created ON bin_stock_levels(created_at)",
    ]:
        conn.execute(sa.text(idx_sql))

    # ── location_allocations ───────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS location_allocations (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id     UUID NOT NULL,
            location_id         UUID NOT NULL REFERENCES warehouse_locations(id),
            item_group_id       UUID NOT NULL,
            priority            INTEGER DEFAULT 0,
            allocation_type     VARCHAR(20) NOT NULL DEFAULT 'preferred',
            is_active           BOOLEAN DEFAULT TRUE,
            created_at          TIMESTAMPTZ DEFAULT now(),
            updated_at          TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT chk_alloc_type CHECK (allocation_type IN ('exclusive', 'preferred'))
        )
    """))

    # Indexes for location_allocations
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_la_org ON location_allocations(organization_id)",
        "CREATE INDEX IF NOT EXISTS idx_la_location ON location_allocations(location_id)",
        "CREATE INDEX IF NOT EXISTS idx_la_item_group ON location_allocations(item_group_id)",
        "CREATE INDEX IF NOT EXISTS idx_la_active ON location_allocations(is_active)",
    ]:
        conn.execute(sa.text(idx_sql))

    # Partial unique index: only one active exclusive allocation per location
    conn.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_la_exclusive
        ON location_allocations(location_id)
        WHERE allocation_type = 'exclusive' AND is_active = TRUE
    """))


def downgrade() -> None:
    op.drop_table('location_allocations')
    op.drop_table('bin_stock_levels')
