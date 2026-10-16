"""Add the QSeal product activated notification type.

Revision ID: 120_add_qseal_product_activated_notification_type
Revises: 119_add_qseal_product_notification_types
"""

from collections.abc import Sequence

from alembic import op


revision: str = "120_add_qseal_product_activated_notification_type"
down_revision: str | Sequence[str] | None = "119_add_qseal_product_notification_types"
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
                WHERE t.typname = 'notificationtype'
                  AND e.enumlabel = 'product_activated'
            ) THEN
                ALTER TYPE notificationtype ADD VALUE 'product_activated';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL does not support dropping individual enum values.
    pass
