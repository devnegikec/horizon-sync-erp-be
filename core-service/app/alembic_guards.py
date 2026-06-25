"""Idempotency helpers for Alembic migrations.

These let migrations be safely (re-)run against databases where some objects
already exist -- e.g. objects created out-of-band, by a partially applied
migration chain, or shared across systems. Each helper inspects the live
database at runtime so guarded operations become no-ops when the target object
is already present.

Usage inside a migration::

    from app.alembic_guards import has_table, has_column

    def upgrade():
        if not has_table("foo"):
            op.create_table("foo", ...)
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


def _bind():
    """Return a live DB bind, preferring the Alembic context if available."""
    try:
        return op.get_bind()
    except Exception:
        from app.config import settings
        from sqlalchemy import create_engine
        return create_engine(settings.database_url)


def _inspector() -> sa.engine.reflection.Inspector:
    return sa.inspect(_bind())


def has_table(table: str) -> bool:
    """Return True if the table exists in the current schema."""
    return table in _inspector().get_table_names()


def has_column(table: str, column: str) -> bool:
    """Return True if the column exists on the table (False if no table)."""
    if not has_table(table):
        return False
    return any(c["name"] == column for c in _inspector().get_columns(table))


def has_index(table: str, index: str) -> bool:
    """Return True if an index with the given name exists on the table."""
    if not has_table(table):
        return False
    return any(i["name"] == index for i in _inspector().get_indexes(table))


def has_constraint(table: str, name: str) -> bool:
    """Return True if a PK/unique/check/foreign-key constraint name exists."""
    if not has_table(table):
        return False
    insp = _inspector()
    names: set[str] = set()
    pk = insp.get_pk_constraint(table)
    if pk.get("name"):
        names.add(pk["name"])
    names.update(c["name"] for c in insp.get_unique_constraints(table) if c.get("name"))
    names.update(c["name"] for c in insp.get_check_constraints(table) if c.get("name"))
    names.update(fk["name"] for fk in insp.get_foreign_keys(table) if fk.get("name"))
    return name in names


def has_type(type_name: str) -> bool:
    """Return True if a Postgres type (e.g. an enum) with this name exists."""
    bind = _bind()
    # In Alembic context bind is a Connection; outside it is an Engine.
    if hasattr(bind, "execute"):
        result = bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": type_name})
    else:
        with bind.connect() as conn:
            result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": type_name})
    return result.scalar() is not None


def column_type(table: str, column: str) -> str | None:
    """Return the lower-cased string form of a column's type, or None."""
    if not has_table(table):
        return None
    for c in _inspector().get_columns(table):
        if c["name"] == column:
            return str(c["type"]).lower()
    return None
