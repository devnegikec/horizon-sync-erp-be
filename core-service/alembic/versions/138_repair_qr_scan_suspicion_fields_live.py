"""Repair QSeal suspicion fields using the live database connection.

This is a follow-up to revision 137 for databases where a guarded migration was
recorded while Alembic was connected to a schema that did not expose the
``qr_scan_events`` table.  It deliberately fails when the table is unavailable
so a wrong database or search path cannot look like a successful migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "138_repair_qr_scan_suspicion_fields_live"
down_revision: str | Sequence[str] | None = "137_repair_qr_scan_suspicion_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    table_name = conn.execute(sa.text("SELECT to_regclass('qr_scan_events')")).scalar()
    if table_name is None:
        raise RuntimeError(
            "Migration connected to a database/schema without qr_scan_events. "
            "Run it against the same core_db and search_path used by Core Service."
        )

    conn.execute(
        sa.text(
            "ALTER TABLE qr_scan_events "
            "ADD COLUMN IF NOT EXISTS is_suspicious BOOLEAN NOT NULL DEFAULT FALSE"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE qr_scan_events "
            "ADD COLUMN IF NOT EXISTS risk_score INTEGER NOT NULL DEFAULT 0"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE qr_scan_events "
            "ADD COLUMN IF NOT EXISTS suspicious_reasons JSONB NOT NULL "
            "DEFAULT '[]'::jsonb"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE qr_scan_events "
            "ADD COLUMN IF NOT EXISTS review_status VARCHAR(20) NOT NULL "
            "DEFAULT 'not_flagged'"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE qr_scan_events "
            "ADD COLUMN IF NOT EXISTS flagged_at TIMESTAMPTZ"
        )
    )

    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_qr_scan_events_is_suspicious "
            "ON qr_scan_events (is_suspicious)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_qr_scan_events_risk_score "
            "ON qr_scan_events (risk_score)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_qr_scan_events_review_status "
            "ON qr_scan_events (review_status)"
        )
    )


def downgrade() -> None:
    # Revision 137 owns the schema objects; this follow-up only repairs them.
    pass
