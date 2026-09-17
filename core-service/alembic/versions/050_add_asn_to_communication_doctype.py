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
    # The communicationdoctype enum is materialized by communication_logs
    # (see 056_create_missing_erp_tables) with create_type=False, so on fresh
    # databases this migration can run BEFORE the type exists. Create the full
    # enum (already including 'asn') when missing; otherwise append 'asn' if it
    # isn't present yet. Fully idempotent and order-independent.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'communicationdoctype'
            ) THEN
                CREATE TYPE communicationdoctype AS ENUM (
                    'quotation', 'sales_order', 'purchase_order', 'invoice',
                    'delivery_note', 'purchase_receipt', 'payment', 'rfq',
                    'material_request', 'asn'
                );
            ELSIF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'communicationdoctype' AND e.enumlabel = 'asn'
            ) THEN
                ALTER TYPE communicationdoctype ADD VALUE 'asn';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # PostgreSQL does not support dropping individual enum values.
    # To remove 'asn', the enum would need to be fully recreated.
    pass
