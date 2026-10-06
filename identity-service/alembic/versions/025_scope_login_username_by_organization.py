"""Enforce per-organization login_username uniqueness at the database level.

Revision ID: 025
Revises: 024
Create Date: 2026-10-03

Migration 024 dropped the global unique index on ``users.login_username`` and
left uniqueness to application checks, which can race under concurrent worker
creation. This adds a denormalized ``organization_id`` to ``users`` (the
worker's primary organization) and a partial unique index on
``(organization_id, login_username)`` so the database guarantees uniqueness
within an organization.
"""

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Add the denormalized organization_id column.
    op.add_column(
        "users",
        sa.Column("organization_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    # 2. Backfill from each worker's primary user_organization_roles row.
    conn.execute(
        text(
            """
            UPDATE users u
            SET organization_id = sub.organization_id
            FROM (
                SELECT DISTINCT ON (user_id) user_id, organization_id
                FROM user_organization_roles
                WHERE is_active = true
                ORDER BY user_id, is_primary DESC, created_at ASC
            ) sub
            WHERE u.id = sub.user_id
            """
        )
    )

    # 3. Enforce per-organization uniqueness (partial: only when both are set).
    op.execute(
        text(
            "CREATE UNIQUE INDEX uq_users_org_login_username "
            "ON users (organization_id, login_username) "
            "WHERE login_username IS NOT NULL AND organization_id IS NOT NULL"
        )
    )


def downgrade():
    op.execute(text("DROP INDEX IF EXISTS uq_users_org_login_username"))
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_column("users", "organization_id")
