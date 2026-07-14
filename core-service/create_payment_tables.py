"""Create payment tables directly in database"""

import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)


def main():
    engine = create_engine(DATABASE_URL)

    with engine.begin() as conn:
        print("Creating payment enum types...")

        # Create enum types
        conn.execute(
            text("""
            DO $$ BEGIN
                CREATE TYPE payment_type AS ENUM ('Customer_Payment', 'Supplier_Payment');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        )

        conn.execute(
            text("""
            DO $$ BEGIN
                CREATE TYPE payment_mode AS ENUM ('Cash', 'Check', 'Bank_Transfer');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        )

        conn.execute(
            text("""
            DO $$ BEGIN
                CREATE TYPE payment_status AS ENUM ('Draft', 'Confirmed', 'Cancelled');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        )

        conn.execute(
            text("""
            DO $$ BEGIN
                CREATE TYPE payment_source AS ENUM ('Manual', 'Stripe', 'Razorpay');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        )

        print("✅ Created enum types")

        print("\nCreating payment_entries table...")
        conn.execute(
            text("""
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
        """)
        )
        print("✅ Created payment_entries table")

        print("\nCreating indexes...")
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_payment_entries_org_date ON payment_entries(organization_id, payment_date)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_payment_entries_org_party ON payment_entries(organization_id, party_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_payment_entries_org_status ON payment_entries(organization_id, status)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_payment_entries_reference ON payment_entries(reference_no)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_payment_entries_receipt ON payment_entries(receipt_number)"
            )
        )
        print("✅ Created indexes")

        print("\nCreating payment_references table...")
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS payment_references (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL,
                payment_id UUID NOT NULL,
                invoice_id UUID NOT NULL,
                allocated_amount NUMERIC(15, 2) NOT NULL,
                exchange_rate NUMERIC(15, 6) DEFAULT 1.0,
                allocated_amount_invoice_currency NUMERIC(15, 2),
                created_by UUID NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

                CONSTRAINT check_payment_references_amount CHECK (allocated_amount > 0),
                CONSTRAINT uq_payment_references_payment_invoice UNIQUE (payment_id, invoice_id)
            )
        """)
        )
        print("✅ Created payment_references table")

        print("\nCreating payment_references indexes...")
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_payment_references_payment ON payment_references(payment_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_payment_references_invoice ON payment_references(invoice_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_payment_references_org ON payment_references(organization_id)"
            )
        )
        print("✅ Created payment_references indexes")

        print("\nCreating payment_audit_log table...")
        conn.execute(
            text("""
            DO $$ BEGIN
                CREATE TYPE payment_audit_action AS ENUM ('CREATE', 'UPDATE', 'CONFIRM', 'CANCEL', 'ALLOCATE', 'DEALLOCATE');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        )

        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS payment_audit_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL,
                payment_id UUID NOT NULL,
                action payment_audit_action NOT NULL,
                user_id UUID NOT NULL,
                old_values JSONB,
                new_values JSONB,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """)
        )
        print("✅ Created payment_audit_log table")

        print("\nCreating payment_audit_log indexes...")
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_payment_audit_log_payment_time ON payment_audit_log(payment_id, timestamp)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_payment_audit_log_org_time ON payment_audit_log(organization_id, timestamp)"
            )
        )
        print("✅ Created payment_audit_log indexes")

        print("\n✅ All payment tables created successfully!")


if __name__ == "__main__":
    main()
