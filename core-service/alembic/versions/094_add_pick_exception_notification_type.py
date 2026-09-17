"""Add pick_exception to notificationtype enum

Revision ID: 094_add_pick_exception_notification_type
Revises: 093_add_pick_idempotency
Create Date: 2026-08-29

Extends the ``notificationtype`` PostgreSQL enum with ``pick_exception`` so the
supervisor queue (PR-09 / T-03, Q11) can deliver in-app exception alerts via
the existing NotificationService.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "094_add_pick_exception_notification_type"
down_revision: str | Sequence[str] | None = "093_add_pick_idempotency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'notificationtype' AND e.enumlabel = 'pick_exception'
            ) THEN
                ALTER TYPE notificationtype ADD VALUE 'pick_exception';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL does not support dropping individual enum values.
    pass
