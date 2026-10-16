"""Create the missing ``system_config`` table.

``SystemConfig`` (app/models/system_config.py) is queried by
``CurrencyService.get_base_currency()`` for the ``base_currency`` key, but **no
migration ever created the table**, and the application no longer calls
``Base.metadata.create_all`` anywhere. On any freshly migrated database the table
is therefore absent and:

    GET /api/v1/currency/currencies

fails with ``psycopg2.errors.UndefinedTable: relation "system_config" does not
exist``, which the global SQLAlchemy error handler in app/main.py maps to a 503.
The platform dashboard calls that endpoint on every load, so a fresh environment
shows a 503 immediately. It only ever worked where the table predated the
migration chain (an older ``create_all``-era bootstrap).

No seed row is required: ``get_base_currency()`` falls back to
``CurrencyService.DEFAULT_BASE_CURRENCY`` ("USD") when the ``base_currency`` key
is missing, so only the table itself must exist. ``set_base_currency()`` inserts
the row later, e.g. during organization onboarding.

Guards follow the house style (app/alembic_guards.py), so this is a no-op against
a database that already has the table.

Revision ID: 132_add_system_config
Revises: 131_add_floor_plan_layout_doc
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_table

revision: str = "132_add_system_config"
down_revision: str | Sequence[str] | None = "131_add_floor_plan_layout_doc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if has_table("system_config"):
        return

    op.create_table(
        "system_config",
        sa.Column("key", sa.String(100), primary_key=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_by", sa.String(100), nullable=False),
    )


def downgrade() -> None:
    # Intentional: drop only the table this migration created. Existing
    # installations that hand-created the table keep it on rollback because
    # upgrade() is a no-op for them, so downgrade() must be too.
    if not has_table("system_config"):
        return
    op.drop_table("system_config")
