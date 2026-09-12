"""Add transfer_pick_created to notificationtype enum

Revision ID: 105_add_transfer_pick_created_notification_type
Revises: 104_add_asn_linked_stock_entry
Create Date: 2026-08-31

Extends the ``notificationtype`` PostgreSQL enum with ``transfer_pick_created``
so the internal-transfer confirm flow can emit a "Transfer Pick List Created"
notification via NotificationService without failing the ASN update with a
503 (InvalidTextRepresentation on the native enum).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "105_add_transfer_pick_created_notification_type"
down_revision: str | Sequence[str] | None = "104_add_asn_linked_stock_entry"
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
                  AND e.enumlabel = 'transfer_pick_created'
            ) THEN
                ALTER TYPE notificationtype ADD VALUE 'transfer_pick_created';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL does not support dropping individual enum values.
    pass
