"""Scope warehouse worker login_username uniqueness to the organization.

Revision ID: 024
Revises: 023
Create Date: 2026-10-01

``users.login_username`` was globally unique via the partial unique index
``uq_users_login_username`` (created in migration 018). That prevented two
warehouse workers in different organizations from sharing a username.

Drop the global unique index and replace it with a plain (non-unique) index
for lookup performance. Uniqueness is now enforced at the application layer,
scoped to the worker's organization (see ``workers.py`` and
``auth_service.login_worker``).
"""

from sqlalchemy import text

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(text("DROP INDEX IF EXISTS uq_users_login_username"))
    op.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_users_login_username "
            "ON users (login_username)"
        )
    )


def downgrade():
    op.execute(text("DROP INDEX IF EXISTS ix_users_login_username"))
    op.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_login_username "
            "ON users (login_username) WHERE login_username IS NOT NULL"
        )
    )
