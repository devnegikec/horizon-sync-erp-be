"""Add the ``inbound_exception`` in-app notification type.

G-Q2 / E-09: dock exceptions (unreadable QR, duplicate identity, unknown identity,
excess) must alert the warehouse supervisors. The notification type column is a
Postgres enum, so the new value has to be added to the database type as well as
to :class:`app.models.base.NotificationType`.

``ALTER TYPE ... ADD VALUE`` cannot run inside the migration transaction, hence the
``autocommit_block``. The statement is idempotent (``IF NOT EXISTS``) and guarded
by a ``pg_enum`` lookup so it is also safe on databases whose type was created
from the SQLAlchemy model.

Revision ID: 123_notification_inbound_exception
Revises: 122_inbound_exception_reason_codes
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "123_notification_inbound_exception"
down_revision: str | Sequence[str] | None = "122_inbound_exception_reason_codes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_NAME = "notificationtype"
NEW_VALUE = "inbound_exception"

_VALUE_EXISTS = sa.text(
    """
    SELECT 1
      FROM pg_enum e
      JOIN pg_type t ON t.oid = e.enumtypid
     WHERE t.typname = :type_name
       AND e.enumlabel = :label
    """
)


def _value_exists() -> bool:
    return (
        op.get_bind()
        .execute(_VALUE_EXISTS.bindparams(type_name=ENUM_NAME, label=NEW_VALUE))
        .scalar()
        is not None
    )


def upgrade() -> None:
    if _value_exists():
        return
    # Postgres refuses ADD VALUE inside a transaction block, so run it on its own.
    with op.get_context().autocommit_block():
        op.execute(
            sa.text(f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{NEW_VALUE}'")
        )


def downgrade() -> None:
    # Postgres cannot drop a single enum value; removing it would require
    # recreating the type and rewriting every dependent column. The application
    # simply stops emitting the value.
    pass
