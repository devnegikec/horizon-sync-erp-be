"""Alembic environment configuration for Identity Service"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, inspect, pool, text

from alembic import context

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402
from app.models import *  # Import all models  # noqa: E402, F401, F403

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set sqlalchemy.url from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

VERSION_TABLE = "alembic_version_identity"
LEGACY_VERSION_TABLE = "alembic_version"


def _copy_legacy_revision(connection) -> None:
    """Preserve migration state after moving to a service-specific table.

    Existing identity databases used ``alembic_version`` before the service
    adopted ``alembic_version_identity``.  Without copying that revision once,
    Alembic treats a populated database as new and attempts to replay every
    migration from the beginning.
    """
    table_names = set(inspect(connection).get_table_names())
    if VERSION_TABLE in table_names or LEGACY_VERSION_TABLE not in table_names:
        return

    legacy_revisions = connection.execute(
        text(f"SELECT version_num FROM {LEGACY_VERSION_TABLE}")
    ).scalars().all()
    known_revisions = {
        revision.revision for revision in context.script.walk_revisions()
    }
    matching_revisions = [
        revision for revision in legacy_revisions if revision in known_revisions
    ]

    if len(matching_revisions) != 1:
        return

    connection.execute(
        text(
            f"CREATE TABLE {VERSION_TABLE} "
            "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
        )
    )
    connection.execute(
        text(f"INSERT INTO {VERSION_TABLE} (version_num) VALUES (:revision)"),
        {"revision": matching_revisions[0]},
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        with connection.begin():
            _copy_legacy_revision(connection)

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=VERSION_TABLE,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
