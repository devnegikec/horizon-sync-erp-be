"""Idempotent Alembic operation patches.

Monkey-patches alembic.op so that create_* operations silently succeed
when the object already exists. This lets migrations be re-run safely
against an existing schema.
"""

import functools

from alembic import op
from sqlalchemy.exc import ProgrammingError

# PostgreSQL error codes we want to swallow
_DUPLICATE_CODES = {
    "42P07",  # duplicate_table
    "42701",  # duplicate_column
    "42710",  # duplicate_object (index, constraint, type, etc.)
    "42723",  # duplicate_function
}


def _swallow_duplicate(func):
    """Decorator that ignores PostgreSQL "already exists" errors."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ProgrammingError as exc:
            # SQLAlchemy wraps psycopg2 errors in ProgrammingError.
            # The original DBAPI error is usually on .orig
            orig = getattr(exc, "orig", None)
            if orig is not None:
                pgcode = getattr(orig, "pgcode", None)
                if pgcode in _DUPLICATE_CODES:
                    return None
            # Re-raise if it's not a duplicate error
            raise

    return wrapper


def apply_idempotent_patches() -> None:
    """Wrap Alembic operation helpers so duplicates are ignored."""
    op.create_table = _swallow_duplicate(op.create_table)
    op.create_index = _swallow_duplicate(op.create_index)
    op.add_column = _swallow_duplicate(op.add_column)
    op.create_foreign_key = _swallow_duplicate(op.create_foreign_key)
    op.create_unique_constraint = _swallow_duplicate(op.create_unique_constraint)
    op.create_check_constraint = _swallow_duplicate(op.create_check_constraint)
    # Enum / type creation is often done via execute(); we can't patch
    # that generically, but migrations that use CREATE TYPE should use
    # IF NOT EXISTS or wrap execute manually.
