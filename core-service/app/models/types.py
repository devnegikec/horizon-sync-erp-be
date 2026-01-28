"""Custom SQLAlchemy types for cross-database compatibility"""

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB as PostgresJSONB


class JSONB(TypeDecorator):
    """
    Cross-database JSON type.

    Uses PostgreSQL's JSONB when available, falls back to JSON for other databases.
    This allows tests to run with SQLite while production uses PostgreSQL.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresJSONB())
        else:
            return dialect.type_descriptor(JSON())
