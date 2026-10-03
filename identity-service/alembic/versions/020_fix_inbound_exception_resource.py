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


_UPDATE_INBOUND_EXCEPTION = (
    "UPDATE permissions SET resource = 'inbound_exception'::resourcetype "
    "WHERE code LIKE 'inbound_exception.%' AND resource::text = 'warehouse'"
)


def upgrade():
    bind = op.get_bind()
    engine = _bind_engine(bind)

    # ``resourcetype`` is created by migration 001.  On a fresh database the
    # entire migration chain runs inside a single open transaction, so the type
    # (and every value added to it) is not yet committed and is therefore
    # invisible to a separate connection.  On an existing database that is
    # already stamped at 019, the type is committed.
    #
    # These two cases need different handling because PostgreSQL forbids using
    # a newly added enum value in the same transaction it was added *unless*
    # the type itself was also created in that same transaction.
    with engine.connect() as probe:
        type_committed = (
            probe.execute(
                text("SELECT 1 FROM pg_type WHERE typname = 'resourcetype'")
            ).scalar()
            is not None
        )

    if type_committed:
        # Existing DB: add the value on an AUTOCOMMIT connection so it is
        # committed before the UPDATE tries to use it.
        with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
            conn.execute(
                text(
                    "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'inbound_exception'"
                )
            )
        op.execute(text(_UPDATE_INBOUND_EXCEPTION))
    else:
        # Fresh DB: both statements must run on the main migration connection.
        op.execute(
            text("ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'inbound_exception'")
        )
        op.execute(text(_UPDATE_INBOUND_EXCEPTION))


def downgrade():
    # Only casts back to 'warehouse', a pre-existing value, so it is safe on
    # the main migration connection in both fresh and existing databases.
    op.execute(
        text(
            "UPDATE permissions SET resource = 'warehouse'::resourcetype "
            "WHERE code LIKE 'inbound_exception.%' AND resource::text = 'inbound_exception'"
        )
    )
