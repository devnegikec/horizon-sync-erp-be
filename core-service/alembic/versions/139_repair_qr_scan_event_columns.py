"""Repair any remaining columns mapped by the QR scan event ORM model.

The history and summary endpoints count an ORM query for ``QRScanEvent``.  A
count over that query still selects the model's mapped columns in a subquery,
so one missing legacy column can fail both endpoints while narrower analytics
queries continue to work.  This revision repairs all additive QR scan-event
columns in one live-database pass.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "139_repair_qr_scan_event_columns"
down_revision: str | Sequence[str] | None = "138_repair_qr_scan_suspicion_fields_live"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# These are additive columns from revisions 062, 068, 069, 115, 116, and 128.
# Existing columns are left untouched by ``IF NOT EXISTS``.
_COLUMNS = (
    ("user_agent_raw", "TEXT"),
    ("user_agent_parsed", "JSONB"),
    ("qr_type", "VARCHAR(30)"),
    ("cta_action", "VARCHAR(50)"),
    ("referrer_url", "TEXT"),
    ("language", "VARCHAR(10)"),
    ("event_id", "UUID"),
    ("verification_status", "VARCHAR(40)"),
    ("authentic", "BOOLEAN"),
    ("qr_channel", "VARCHAR(10)"),
    ("ip_hash", "VARCHAR(64)"),
    ("is_bot", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("location_source", "VARCHAR(20)"),
    ("location_accuracy_meters", "INTEGER"),
    ("street_address", "TEXT"),
    ("product_id", "UUID"),
    ("block_id", "UUID"),
    ("qseal_track_id", "UUID"),
    ("qseal_parameter_id", "UUID"),
    ("batch", "VARCHAR(50)"),
    ("qseal_type", "VARCHAR(30)"),
    ("asn_order_id", "UUID"),
    ("scan_session_id", "UUID"),
    ("dispatch_record_id", "UUID"),
    ("is_suspicious", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("risk_score", "INTEGER NOT NULL DEFAULT 0"),
    ("suspicious_reasons", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
    ("review_status", "VARCHAR(20) NOT NULL DEFAULT 'not_flagged'"),
    ("flagged_at", "TIMESTAMPTZ"),
)


def upgrade() -> None:
    conn = op.get_bind()
    table_name = conn.execute(sa.text("SELECT to_regclass('qr_scan_events')")).scalar()
    if table_name is None:
        raise RuntimeError(
            "Migration connected to a database/schema without qr_scan_events. "
            "Run it against the same core_db and search_path used by Core Service."
        )

    for column_name, column_definition in _COLUMNS:
        conn.execute(
            sa.text(
                f"ALTER TABLE qr_scan_events ADD COLUMN IF NOT EXISTS "
                f"{column_name} {column_definition}"
            )
        )

    # Indexes owned by revisions 115 and 068. A drifted database has the columns
    # but not their indexes, so filtered QSeal analytics degrade to full scans.
    for index_name, column_name in (
        ("ix_qr_scan_events_product_id", "product_id"),
        ("ix_qr_scan_events_block_id", "block_id"),
        ("ix_qr_scan_events_qseal_track_id", "qseal_track_id"),
        ("ix_qr_scan_events_qseal_parameter_id", "qseal_parameter_id"),
        ("ix_qr_scan_events_batch", "batch"),
        ("ix_qr_scan_events_qseal_type", "qseal_type"),
        ("ix_qr_scan_events_verification_status", "verification_status"),
    ):
        conn.execute(
            sa.text(
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                f"ON qr_scan_events ({column_name})"
            )
        )

    # ``event_id`` only provides its idempotency guarantee together with the
    # unique partial index created by revision 068. A drifted database stamped
    # past 068 has the column but not the index, which would let concurrent
    # retries insert duplicate scan events.
    conn.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_qr_scan_events_event_id "
            "ON qr_scan_events (event_id) WHERE event_id IS NOT NULL"
        )
    )


def downgrade() -> None:
    # This revision only repairs additive columns. The owning migrations remain
    # responsible for their normal downgrade behavior.
    pass
