"""add payment_entries table (ensure table exists on main migration head)

Revision ID: p8q7r6s5t4u3
Revises: i9j0k1l2m3n4
Create Date: 2026-02-26

The payment_entries table was originally in g7h8i9j0k1l2, which is on a branch
that is not applied when running 'alembic upgrade head'. This migration creates
payment_entries (and required enums) if not exists, so GET /api/v1/payments works.
"""
from alembic import op
import sqlalchemy as sa

revision = "p8q7r6s5t4u3"
down_revision = "i9j0k1l2m3n4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    # Create payment_type enum if it doesn't exist
    connection.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE payment_type AS ENUM ('Customer_Payment', 'Supplier_Payment');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))

    # Create payment_mode enum if it doesn't exist
    connection.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE payment_mode AS ENUM ('Cash', 'Check', 'Bank_Transfer');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))

    # Create payment_status enum if it doesn't exist
    connection.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE payment_status AS ENUM ('Draft', 'Confirmed', 'Cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))

    # Create payment_source enum if it doesn't exist
    connection.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE payment_source AS ENUM ('Manual', 'Stripe', 'Razorpay');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))

    # Create payment_entries table if not exists (FKs only if organizations/users exist)
    connection.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS payment_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            payment_type payment_type NOT NULL,
            party_id UUID NOT NULL,
            amount NUMERIC(15, 2) NOT NULL,
            currency_code VARCHAR(3) NOT NULL DEFAULT 'USD',
            payment_date TIMESTAMP WITH TIME ZONE NOT NULL,
            payment_mode payment_mode NOT NULL,
            reference_no VARCHAR(100),
            status payment_status NOT NULL DEFAULT 'Draft',
            source payment_source NOT NULL DEFAULT 'Manual',
            gateway_transaction_id VARCHAR(200),
            receipt_number VARCHAR(50) UNIQUE,
            cancellation_reason TEXT,
            cancelled_by UUID,
            cancelled_at TIMESTAMP WITH TIME ZONE,
            created_by UUID NOT NULL,
            updated_by UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT check_payment_entries_amount CHECK (amount > 0),
            CONSTRAINT check_payment_entries_reference_no CHECK (
                (payment_mode IN ('Check', 'Bank_Transfer') AND reference_no IS NOT NULL) OR
                (payment_mode = 'Cash')
            ),
            CONSTRAINT check_payment_entries_gateway_transaction CHECK (
                (source IN ('Stripe', 'Razorpay') AND gateway_transaction_id IS NOT NULL) OR
                (source = 'Manual')
            )
        )
    """))

    # Create indexes if not exist
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_payment_entries_org_date
        ON payment_entries(organization_id, payment_date)
    """))
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_payment_entries_org_party
        ON payment_entries(organization_id, party_id)
    """))
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_payment_entries_org_status
        ON payment_entries(organization_id, status)
    """))
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_payment_entries_reference
        ON payment_entries(reference_no)
    """))
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_payment_entries_receipt
        ON payment_entries(receipt_number)
    """))


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_payment_entries_receipt"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_payment_entries_reference"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_payment_entries_org_status"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_payment_entries_org_party"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_payment_entries_org_date"))
    connection.execute(sa.text("DROP TABLE IF EXISTS payment_entries"))
