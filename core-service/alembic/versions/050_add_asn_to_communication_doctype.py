"""add_asn_to_communication_doctype

Revision ID: 050_add_asn_to_communication_doctype
Revises: 049_add_asn_orders_table
Create Date: 2026-05-28 15:46:55.550308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '050_add_asn_to_communication_doctype'
down_revision: Union[str, None] = '049_add_asn_orders_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Some installations never created the legacy communicationdoctype enum.
    # In that case there is nothing to extend; later migrations do not depend
    # on this enum being present.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typnamespace = 'public'::regnamespace
                  AND typname = 'communicationdoctype'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typnamespace = 'public'::regnamespace
                  AND t.typname = 'communicationdoctype'
                  AND e.enumlabel = 'asn'
            ) THEN
                ALTER TYPE public.communicationdoctype ADD VALUE 'asn';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL does not support dropping individual enum values.
    # To remove 'asn', the enum would need to be fully recreated.
    pass
