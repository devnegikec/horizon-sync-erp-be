"""Idempotency layer for Alembic migrations.

Wraps the common ``alembic.op`` creation helpers so that re-running a
migration against a database where the object already exists becomes a
no-op instead of raising ``DuplicateTable`` / ``DuplicateColumn`` /
``DuplicateObject`` errors.

This is applied centrally from ``env.py`` (online mode only), so it covers
*every* existing migration and any future ones without having to add manual
``IF EXISTS`` guards to each individual revision.

Covered operations:
    - op.create_table            (skip if table exists)
    - op.create_index            (skip if index exists)
    - op.add_column              (skip if column exists)
    - op.create_unique_constraint
    - op.create_foreign_key
    - op.create_check_constraint
    - op.create_primary_key      (skip if a constraint of that name exists)
    - op.execute("CREATE TYPE ... AS ENUM ...")  (wrapped in IF NOT EXISTS)

Only "create"-style operations are guarded — drops are left untouched.
"""

import re

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

_PATCHED = False


def _inspector():
    return inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    try:
        return _inspector().has_table(table_name)
    except Exception:
        return False


def _column_exists(table_name: str, column_name: str) -> bool:
    try:
        cols = {c["name"] for c in _inspector().get_columns(table_name)}
        return column_name in cols
    except Exception:
        return False


def _index_exists(table_name: str, index_name: str) -> bool:
    try:
        insp = _inspector()
        names = {i["name"] for i in insp.get_indexes(table_name)}
        # Unique constraints are sometimes backed by indexes of the same name.
        names |= {u["name"] for u in insp.get_unique_constraints(table_name)}
        return index_name in names
    except Exception:
        return False


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not constraint_name:
        return False
    try:
        insp = _inspector()
        names: set = set()
        names |= {u["name"] for u in insp.get_unique_constraints(table_name)}
        names |= {f["name"] for f in insp.get_foreign_keys(table_name)}
        try:
            names |= {c["name"] for c in insp.get_check_constraints(table_name)}
        except Exception:
            pass
        pk = insp.get_pk_constraint(table_name)
        if pk and pk.get("name"):
            names.add(pk["name"])
        return constraint_name in names
    except Exception:
        return False


def apply_idempotent_patches() -> None:
    """Monkeypatch op.* creation helpers to be idempotent. Safe to call once."""
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    _create_table = op.create_table
    _create_index = op.create_index
    _add_column = op.add_column
    _create_unique = op.create_unique_constraint
    _create_fk = op.create_foreign_key
    _create_check = op.create_check_constraint
    _create_pk = op.create_primary_key
    _execute = op.execute

    def create_table(table_name, *columns, **kw):
        if _table_exists(table_name):
            print(f"[idempotent] table '{table_name}' exists — skipping create_table")
            return None
        return _create_table(table_name, *columns, **kw)

    def create_index(index_name, table_name, *args, **kw):
        if _index_exists(table_name, index_name):
            print(f"[idempotent] index '{index_name}' exists — skipping create_index")
            return None
        return _create_index(index_name, table_name, *args, **kw)

    def add_column(table_name, column, **kw):
        col_name = getattr(column, "name", None)
        if col_name and _column_exists(table_name, col_name):
            print(
                f"[idempotent] column '{table_name}.{col_name}' exists — skipping add_column"
            )
            return None
        return _add_column(table_name, column, **kw)

    def create_unique_constraint(constraint_name, table_name, *args, **kw):
        if _constraint_exists(table_name, constraint_name):
            print(
                f"[idempotent] constraint '{constraint_name}' exists — skipping create_unique_constraint"
            )
            return None
        return _create_unique(constraint_name, table_name, *args, **kw)

    def create_foreign_key(constraint_name, source_table, *args, **kw):
        if _constraint_exists(source_table, constraint_name):
            print(
                f"[idempotent] constraint '{constraint_name}' exists — skipping create_foreign_key"
            )
            return None
        return _create_fk(constraint_name, source_table, *args, **kw)

    def create_check_constraint(constraint_name, table_name, *args, **kw):
        if _constraint_exists(table_name, constraint_name):
            print(
                f"[idempotent] constraint '{constraint_name}' exists — skipping create_check_constraint"
            )
            return None
        return _create_check(constraint_name, table_name, *args, **kw)

    def create_primary_key(constraint_name, table_name, *args, **kw):
        if _constraint_exists(table_name, constraint_name):
            print(
                f"[idempotent] constraint '{constraint_name}' exists — skipping create_primary_key"
            )
            return None
        return _create_pk(constraint_name, table_name, *args, **kw)

    _create_type_re = re.compile(
        r"^\s*CREATE\s+TYPE\s+(?P<name>[\w\".]+)\s+AS\s+ENUM", re.IGNORECASE
    )

    def execute(sqltext, *args, **kw):
        raw = getattr(sqltext, "text", sqltext)
        if isinstance(raw, str):
            m = _create_type_re.match(raw)
            if m:
                type_name = m.group("name").replace('"', "").split(".")[-1]
                body = raw.strip().rstrip(";")
                guarded = (
                    "DO $$ BEGIN "
                    f"IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{type_name}') THEN "
                    f"{body}; "
                    "END IF; END $$;"
                )
                return _execute(sa.text(guarded), *args, **kw)
        return _execute(sqltext, *args, **kw)

    op.create_table = create_table
    op.create_index = create_index
    op.add_column = add_column
    op.create_unique_constraint = create_unique_constraint
    op.create_foreign_key = create_foreign_key
    op.create_check_constraint = create_check_constraint
    op.create_primary_key = create_primary_key
    op.execute = execute
