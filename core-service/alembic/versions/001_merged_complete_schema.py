"""Merged complete schema - consolidates all previous migration heads

Revision ID: 001_merged_complete_schema
Revises: None
Create Date: 2026-02-27

This migration merges all the previous migration heads into a single comprehensive schema.
It includes all tables from the currency/UOM branch (n4o5p6q7r8s9t0) and the main development
branch (465d2a56e62e), creating a clean baseline migration.

Tables created:
- accounts (with AccountType/AccountStatus enums)
- payment_entries (with payment enums)
- currency_masters
- exchange_rates
- uoms
- uom_conversions
- And all performance indexes and constraints
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_merged_complete_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables and indexes from merged heads"""
    connection = op.get_bind()

    # Check which tables already exist so we can skip them
    from sqlalchemy.engine.reflection import Inspector

    inspector = Inspector.from_engine(connection)
    existing_tables = set(inspector.get_table_names())

    # ======================
    # ENUMS
    # ======================

    # Account enums
    connection.execute(
        sa.text("""
        DO $$ BEGIN
            CREATE TYPE accounttype AS ENUM (
                'ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    )

    connection.execute(
        sa.text("""
        DO $$ BEGIN
            CREATE TYPE accountstatus AS ENUM (
                'ACTIVE', 'INACTIVE', 'ARCHIVED'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    )

    # Payment enums
    connection.execute(
        sa.text("""
        DO $$ BEGIN
            CREATE TYPE payment_type AS ENUM ('Customer_Payment', 'Supplier_Payment');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    )

    connection.execute(
        sa.text("""
        DO $$ BEGIN
            CREATE TYPE payment_mode AS ENUM ('Cash', 'Check', 'Bank_Transfer');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    )

    connection.execute(
        sa.text("""
        DO $$ BEGIN
            CREATE TYPE payment_status AS ENUM ('Draft', 'Confirmed', 'Cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    )

    connection.execute(
        sa.text("""
        DO $$ BEGIN
            CREATE TYPE payment_source AS ENUM ('Manual', 'Stripe', 'Razorpay');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    )

    # ======================
    # TABLES
    # ======================

    # Accounts table
    connection.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS accounts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            account_code VARCHAR(50) NOT NULL,
            account_name VARCHAR(200) NOT NULL,
            account_type accounttype NOT NULL,
            parent_account_id UUID,
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            status accountstatus NOT NULL DEFAULT 'ACTIVE',
            is_posting_account BOOLEAN NOT NULL DEFAULT true,
            level INTEGER DEFAULT 0,
            is_group BOOLEAN DEFAULT false,
            description TEXT,
            created_by VARCHAR(100) NOT NULL,
            updated_by VARCHAR(100) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_accounts_parent_account_id FOREIGN KEY (parent_account_id) REFERENCES accounts(id)
        )
    """)
    )

    # Currency masters table
    if "currency_masters" not in existing_tables:
        op.create_table(
            "currency_masters",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("code", sa.String(3), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("symbol", sa.String(5), nullable=True),
            sa.Column(
                "is_base_currency", sa.Boolean, nullable=False, server_default="false"
            ),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                default=sa.func.now(),
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    # Exchange rates table
    if "exchange_rates" not in existing_tables:
        op.create_table(
            "exchange_rates",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("from_currency", sa.String(3), nullable=False),
            sa.Column("to_currency", sa.String(3), nullable=False),
            sa.Column("rate", sa.Numeric(19, 6), nullable=False),
            sa.Column("effective_date", sa.Date, nullable=False),
            sa.Column(
                "captured_at",
                sa.DateTime(timezone=True),
                nullable=True,
                default=sa.func.now(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "from_currency",
                "to_currency",
                "effective_date",
                name="uq_exchange_rate_currency_date",
            ),
            sa.CheckConstraint("rate > 0", name="ck_exchange_rate_positive"),
        )

    # UOMs table
    if "uoms" not in existing_tables:
        op.create_table(
            "uoms",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("abbreviation", sa.String(10), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                default=sa.func.now(),
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    # UOM conversions table
    if "uom_conversions" not in existing_tables:
        op.create_table(
            "uom_conversions",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "item_id", postgresql.UUID(as_uuid=True), nullable=False
            ),  # Note: FK to items table if it exists
            sa.Column("from_uom", sa.String(50), nullable=False),
            sa.Column("to_uom", sa.String(50), nullable=False),
            sa.Column("conversion_factor", sa.Numeric(19, 6), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                default=sa.func.now(),
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "conversion_factor > 0", name="ck_uom_conv_positive_factor"
            ),
        )

    # Payment entries table
    connection.execute(
        sa.text("""
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

    # ======================
    # INDEXES
    # ======================

    # Accounts indexes
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_accounts_organization_id ON accounts (organization_id)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_accounts_account_code ON accounts (account_code)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_accounts_account_type ON accounts (account_type)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_accounts_parent_account_id ON accounts (parent_account_id)"
        )
    )
    connection.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_accounts_status ON accounts (status)")
    )

    # Performance indexes for accounts
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_accounts_org_type ON accounts (organization_id, account_type)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_accounts_org_status ON accounts (organization_id, status)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_accounts_org_code ON accounts (organization_id, account_code)"
        )
    )

    # Currency masters indexes
    if "currency_masters" not in existing_tables:
        op.create_index(
            "ix_currency_masters_org_id", "currency_masters", ["organization_id"]
        )
        op.create_index(
            "ix_currency_masters_organization_id",
            "currency_masters",
            ["organization_id"],
        )
        op.create_index(
            "uq_currency_org_code",
            "currency_masters",
            ["organization_id", "code"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )

    # Exchange rates indexes
    if "exchange_rates" not in existing_tables:
        op.create_index(
            "ix_exchange_rates_org_id", "exchange_rates", ["organization_id"]
        )
        op.create_index(
            "ix_exchange_rates_currencies",
            "exchange_rates",
            ["from_currency", "to_currency"],
        )
        op.create_index(
            "ix_exchange_rates_effective_date", "exchange_rates", ["effective_date"]
        )

    # UOMs indexes
    if "uoms" not in existing_tables:
        op.create_index("ix_uoms_org_id", "uoms", ["organization_id"])
        op.create_index("ix_uoms_organization_id", "uoms", ["organization_id"])
        op.create_index(
            "uq_uom_org_name",
            "uoms",
            ["organization_id", "name"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )
        op.create_index(
            "uq_uom_org_abbr",
            "uoms",
            ["organization_id", "abbreviation"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )

    # UOM conversions indexes
    if "uom_conversions" not in existing_tables:
        op.create_index(
            "ix_uom_conversions_organization_id", "uom_conversions", ["organization_id"]
        )
        op.create_index("ix_uom_conversions_item", "uom_conversions", ["item_id"])
        op.create_index(
            "uq_uom_conv_org_item_pair",
            "uom_conversions",
            ["organization_id", "item_id", "from_uom", "to_uom"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )

    # Payment entries indexes
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_payment_entries_org_date ON payment_entries(organization_id, payment_date)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_payment_entries_org_party ON payment_entries(organization_id, party_id)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_payment_entries_org_status ON payment_entries(organization_id, status)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_payment_entries_reference ON payment_entries(reference_no)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_payment_entries_receipt ON payment_entries(receipt_number)"
        )
    )

    # ======================
    # CONSTRAINTS
    # ======================

    # Accounts unique constraint
    connection.execute(
        sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_accounts_organization_account_code') THEN
                ALTER TABLE accounts ADD CONSTRAINT uq_accounts_organization_account_code UNIQUE (organization_id, account_code);
            END IF;
        END $$;
    """)
    )

    print("✅ All tables, indexes, and constraints created successfully")
    print("📋 Tables created:")
    print("   - accounts (with AccountType/AccountStatus enums)")
    print("   - currency_masters")
    print("   - exchange_rates")
    print("   - uoms")
    print("   - uom_conversions")
    print("   - payment_entries (with payment enums)")
    print("🚀 Database schema is now unified under single migration!")


def downgrade() -> None:
    """Drop all tables and enums"""
    connection = op.get_bind()

    # Drop tables in reverse order (considering FKs)
    connection.execute(sa.text("DROP TABLE IF EXISTS payment_entries"))
    op.drop_table("uom_conversions")
    op.drop_table("uoms")
    op.drop_table("exchange_rates")
    op.drop_table("currency_masters")
    connection.execute(sa.text("DROP TABLE IF EXISTS accounts"))

    # Drop enums
    connection.execute(sa.text("DROP TYPE IF EXISTS payment_source"))
    connection.execute(sa.text("DROP TYPE IF EXISTS payment_status"))
    connection.execute(sa.text("DROP TYPE IF EXISTS payment_mode"))
    connection.execute(sa.text("DROP TYPE IF EXISTS payment_type"))
    connection.execute(sa.text("DROP TYPE IF EXISTS accountstatus"))
    connection.execute(sa.text("DROP TYPE IF EXISTS accounttype"))

    print("🗑️ All tables and enums dropped successfully")
