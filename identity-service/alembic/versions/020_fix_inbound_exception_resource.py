"""Fix inbound_exception permissions to use their own resource type.

Revision ID: 020
Revises: 019
Create Date: 2026-09-04

The ``inbound_exception.*`` permissions were inserted (migration 017) with
``resource='warehouse'`` because no dedicated enum value existed. That makes
them collide with the real ``warehouse.*`` permissions in
``get_permissions_grouped_by_category`` (whose dedup is keyed on
``resource + action``), so inbound exceptions were silently dropped from the
grouped permission picker and fell into the "Other permissions" catch-all.

Adds an ``inbound_exception`` resourcetype value and re-points those rows at it.
"""

from sqlalchemy import text

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def _bind_engine(bind):
    """Return a raw Engine from an Alembic bind (Connection or Engine)."""
    return getattr(bind, "engine", bind)


def upgrade():
    # ALTER TYPE ... ADD VALUE must be committed before the new value can be
    # used, so run both statements on an AUTOCOMMIT connection.
    bind = op.get_bind()
    engine = _bind_engine(bind)
    with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
        conn.execute(
            text(
                "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'inbound_exception'"
            )
        )
        conn.execute(
            text(
                "UPDATE permissions SET resource = 'inbound_exception'::resourcetype "
                "WHERE code LIKE 'inbound_exception.%' AND resource::text = 'warehouse'"
            )
        )


def downgrade():
    bind = op.get_bind()
    engine = _bind_engine(bind)
    with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
        conn.execute(
            text(
                "UPDATE permissions SET resource = 'warehouse'::resourcetype "
                "WHERE code LIKE 'inbound_exception.%' AND resource::text = 'inbound_exception'"
            )
        )
