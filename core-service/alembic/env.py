"""Alembic environment configuration for Core Service"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

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
        version_table="core_alembic_version",
        version_table_pk_length=255,
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

    # Ensure the version table exists with a version_num column wide enough
    # for our long revision IDs (alembic's default is VARCHAR(32), which is
    # too short for e.g. '035_add_subscription_billing_fields'). Do this on a
    # separate autocommit-style connection so it is committed before the
    # migration transaction begins.
    with connectable.connect() as ddl_connection:
        ddl_connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS core_alembic_version "
                "(version_num VARCHAR(255) NOT NULL PRIMARY KEY)"
            )
        )
        ddl_connection.execute(
            text(
                "ALTER TABLE core_alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(255)"
            )
        )
        ddl_connection.commit()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="core_alembic_version",
            version_table_pk_length=255,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
