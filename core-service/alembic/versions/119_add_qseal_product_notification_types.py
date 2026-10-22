"""Add QSeal product lifecycle notification types.

Revision ID: 119_add_qseal_product_notification_types
Revises: 118_add_item_group_default_uom_cache
"""

from collections.abc import Sequence

from alembic import op


revision: str = "119_add_qseal_product_notification_types"
down_revision: str | Sequence[str] | None = "118_add_item_group_default_uom_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for value in ("product_created", "product_updated", "product_deactivated"):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = 'notificationtype' AND e.enumlabel = '{value}'
                ) THEN
                    ALTER TYPE notificationtype ADD VALUE '{value}';
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    # PostgreSQL does not support dropping individual enum values.
    pass
