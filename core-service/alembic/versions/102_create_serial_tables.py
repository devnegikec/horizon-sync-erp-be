"""Create missing serial_nos and serial_no_history tables.

Revision ID: 102
Revises: 101_add_asn_linked_pick_list
Create Date: 2026-08-31

The ``SerialNo`` / ``SerialNoHistory`` models were never materialized by any
alembic migration (they were historically created out-of-band via
``Base.metadata.create_all``). A fresh/re-synced database therefore lacks these
tables, causing ``UndefinedTable: serial_no_history`` on serial tracking and the
internal-transfer EPCIS export. This migration materializes both tables from the
model metadata. Idempotent via ``checkfirst=True``.
"""

from alembic import op

revision = "102_create_serial_tables"
down_revision = "101_add_asn_linked_pick_list"
branch_labels = None
depends_on = None

TABLES = ["serial_nos", "serial_no_history"]


def _target_tables():
    import app.models  # noqa: F401  (registers all models on Base.metadata)
    from app.database import Base

    return [
        Base.metadata.tables[name] for name in TABLES if name in Base.metadata.tables
    ]


def upgrade() -> None:
    bind = op.get_bind()
    from app.database import Base

    Base.metadata.create_all(bind=bind, tables=_target_tables(), checkfirst=True)


def downgrade() -> None:
    # Mirror upgrade's checkfirst behavior: only drop tables that actually
    # exist, and never CASCADE (which would silently delete pre-existing
    # serial data and dependent objects created before this migration ran).
    from sqlalchemy import inspect

    existing = set(inspect(op.get_bind()).get_table_names())
    for name in reversed(TABLES):
        if name in existing:
            op.drop_table(name)
