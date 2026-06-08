"""Reconcile database schema with current SQLAlchemy models

Revision ID: 057_reconcile_schema_with_models
Revises: 056_seed_ai_module_feature_flag
Create Date: 2026-06-07 11:15:00.000000

Some databases were restored from older backups and then stamped forward,
which left them missing tables/columns that newer migrations would have
added (e.g. the ``notifications`` table and ``item_groups.default_valuation_method``).

This migration brings any such database back in line with the current
models WITHOUT touching existing data. It is fully idempotent:

1. Ensures every PostgreSQL ENUM type referenced by the models exists
   (required for columns declared with ``create_type=False``).
2. Creates any missing tables via ``Base.metadata.create_all`` (checkfirst,
   so existing tables are left untouched).
3. Adds any missing columns to already-existing tables. New columns are
   added as NULLABLE so existing rows are unaffected. Each column is added
   inside its own SAVEPOINT so a single problematic column cannot abort the
   whole migration.

Running this repeatedly is safe — it only ever adds what is missing.
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from alembic import op

# Importing the models package populates Base.metadata with every table.
import app.models  # noqa: F401
from app.database import Base

# revision identifiers, used by Alembic.
revision = "057_reconcile_schema_with_models"
down_revision = "055_fix_product_items_token_id_column"
branch_labels = None
depends_on = None


def _collect_enum_types() -> dict:
    """Return {enum_type_name: [values]} for all ENUM columns in the models."""
    enums: dict[str, list[str]] = {}
    for table in Base.metadata.tables.values():
        for col in table.columns:
            type_name = getattr(col.type, "name", None)
            type_values = getattr(col.type, "enums", None)
            if type_name and type_values:
                enums[type_name] = list(type_values)
    return enums


def _ensure_enum_types(conn) -> None:
    for name, values in _collect_enum_types().items():
        labels = ", ".join("'" + str(v).replace("'", "''") + "'" for v in values)
        conn.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = '{name}'
                    ) THEN
                        CREATE TYPE {name} AS ENUM ({labels});
                    END IF;
                END
                $$;
                """
            )
        )


def _create_missing_tables(conn) -> None:
    """Create any tables missing from the DB, resiliently.

    Uses per-table ``create`` (not ``Base.metadata.create_all``) so that a
    single model with an unresolved foreign key cannot abort creation of all
    other tables. Tables are attempted over multiple passes so FK ordering
    resolves itself; any table that still cannot be created (e.g. it references
    a table that does not exist anywhere) is logged and skipped.
    """
    existing = set(inspect(conn).get_table_names())
    pending = [t for t in Base.metadata.tables.values() if t.name not in existing]

    last_errors: dict = {}
    made_progress = True
    while pending and made_progress:
        made_progress = False
        still_pending = []
        for table in pending:
            try:
                with conn.begin_nested():
                    table.create(bind=conn, checkfirst=True)
                print(f"[057] Created missing table {table.name}")
                made_progress = True
            except Exception as exc:
                last_errors[table.name] = exc
                still_pending.append(table)
        pending = still_pending

    for table in pending:
        print(f"[057] Skipped table {table.name}: {last_errors.get(table.name)}")


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Make sure all enum types exist before we create tables / add columns.
    _ensure_enum_types(conn)

    # 2. Create any missing tables (existing tables are skipped).
    _create_missing_tables(conn)

    # 3. Add any missing columns to existing tables.
    #    NOTE: iterate metadata.tables (unordered) rather than sorted_tables —
    #    sorted_tables performs a global FK sort that raises if any model has
    #    an unresolved foreign key, which would abort the whole migration.
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for table in Base.metadata.tables.values():
        if table.name not in existing_tables:
            continue  # just created by _create_missing_tables — already complete

        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            try:
                col_type = col.type.compile(dialect=conn.dialect)
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[057] Could not compile type for {table.name}.{col.name}: {exc}")
                continue

            stmt = (
                f'ALTER TABLE "{table.name}" '
                f'ADD COLUMN IF NOT EXISTS "{col.name}" {col_type}'
            )
            try:
                with conn.begin_nested():
                    conn.execute(sa.text(stmt))
                print(f"[057] Added missing column {table.name}.{col.name}")
            except Exception as exc:
                print(f"[057] Skipped column {table.name}.{col.name}: {exc}")


def downgrade() -> None:
    # No-op: this is a forward-only reconciliation. We never drop columns or
    # tables here because doing so could destroy data that other migrations
    # legitimately created.
    pass