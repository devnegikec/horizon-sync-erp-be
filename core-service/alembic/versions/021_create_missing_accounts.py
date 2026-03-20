"""Create missing accounts and payment_entries tables

Revision ID: 021_create_missing_accounts
Revises: 020_add_bank_account_id_to_payment_entries
Create Date: 2026-03-05

The original migration 001 was skipped due to a stale alembic_version
(i9j0k1l2m3n4) that the normalize script injected. This migration
creates the tables that were supposed to come from 001 and 017 but
never materialised: accounts, payment_entries, account_balances,
default_accounts, account_audit_log, payment_references,
payment_audit_log, bank_accounts, bank_account_history.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.engine.reflection import Inspector

revision = "021_create_missing_accounts"
down_revision = "020_add_bank_account_id_payment"
branch_labels = None
depends_on = None

def _existing(conn):
    return set(Inspector.from_engine(conn).get_table_names())


def upgrade() -> None:
    conn = op.get_bind()
    existing = _existing(conn)

    # ── enums (idempotent) ──────────────────────────────────────────
    for stmt in [
        "CREATE TYPE payment_type AS ENUM ('Customer_Payment','Supplier_Payment')",
        "CREATE TYPE payment_mode AS ENUM ('Cash','Check','Bank_Transfer')",
        "CREATE TYPE payment_status AS ENUM ('Draft','Confirmed','Cancelled')",
        "CREATE TYPE payment_source AS ENUM ('Manual','Stripe','Razorpay')",
        "CREATE TYPE payment_audit_action AS ENUM ('CREATE','UPDATE','CONFIRM','CANCEL','ALLOCATE','DEALLOCATE')",
    ]:
        conn.execute(
            sa.text(
                f"DO $$ BEGIN {stmt}; EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            )
        )

    # ── accounts ──────────────────────────────────────────────────
    if "accounts" not in existing:
        conn.execute(
            sa.text("""
            CREATE TABLE accounts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL,
                account_code VARCHAR(50) NOT NULL,
                account_name VARCHAR(200) NOT NULL,
                account_type accounttype NOT NULL,
                parent_account_id UUID,
                currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                status accountstatus NOT NULL DEFAULT 'ACTIVE',
                is_posting_account BOOLEAN NOT NULL DEFAULT true,
                level INTEGER NOT NULL DEFAULT 1,
                is_group BOOLEAN NOT NULL DEFAULT false,
                description TEXT,
                created_by VARCHAR(100) NOT NULL,
                updated_by VARCHAR(100) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_accounts_parent FOREIGN KEY (parent_account_id) REFERENCES accounts(id),
                CONSTRAINT unique_account_code_per_org UNIQUE (organization_id, account_code)
            )
        """)
        )
        conn.execute(
            sa.text(
                "CREATE INDEX idx_accounts_organization_id ON accounts (organization_id)"
            )
        )
        conn.execute(
            sa.text("CREATE INDEX idx_accounts_account_code ON accounts (account_code)")
        )
        conn.execute(
            sa.text("CREATE INDEX idx_accounts_account_type ON accounts (account_type)")
        )
        conn.execute(
            sa.text(
                "CREATE INDEX idx_accounts_parent_account_id ON accounts (parent_account_id)"
            )
        )
        conn.execute(sa.text("CREATE INDEX idx_accounts_status ON accounts (status)"))
        conn.execute(
            sa.text(
                "CREATE INDEX idx_accounts_org_type ON accounts (organization_id, account_type)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX idx_accounts_org_status ON accounts (organization_id, status)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX idx_accounts_org_code ON accounts (organization_id, account_code)"
            )
        )

    # ── account_balances ────────────────────────────────────────────
    if "account_balances" not in existing:
        op.create_table(
            "account_balances",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "account_id",
                UUID(as_uuid=True),
                sa.ForeignKey("accounts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column(
                "debit_total", sa.Numeric(19, 4), nullable=False, server_default="0"
            ),
            sa.Column(
                "credit_total", sa.Numeric(19, 4), nullable=False, server_default="0"
            ),
            sa.Column("balance", sa.Numeric(19, 4), nullable=False, server_default="0"),
            sa.Column(
                "base_currency_balance",
                sa.Numeric(19, 4),
                nullable=False,
                server_default="0",
            ),
            sa.Column("as_of_date", sa.Date, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime,
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime,
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.UniqueConstraint(
                "account_id", "as_of_date", name="uq_account_balances_account_date"
            ),
        )
        op.create_index(
            "idx_account_balances_account_id", "account_balances", ["account_id"]
        )
        op.create_index(
            "idx_account_balances_as_of_date", "account_balances", ["as_of_date"]
        )
        op.create_index(
            "idx_account_balances_account_date",
            "account_balances",
            ["account_id", "as_of_date"],
        )

    # ── default_accounts ────────────────────────────────────────────
    if "default_accounts" not in existing:
        op.create_table(
            "default_accounts",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("transaction_type", sa.String(100), nullable=False),
            sa.Column("scenario", sa.String(100), nullable=True),
            sa.Column(
                "account_id",
                UUID(as_uuid=True),
                sa.ForeignKey("accounts.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.UniqueConstraint(
                "organization_id",
                "transaction_type",
                "scenario",
                name="uq_default_accounts_org_type_scenario",
            ),
        )
        op.create_index(
            "idx_default_accounts_transaction_type",
            "default_accounts",
            ["transaction_type"],
        )
        op.create_index(
            "idx_default_accounts_scenario", "default_accounts", ["scenario"]
        )
        op.create_index(
            "idx_default_accounts_organization_id",
            "default_accounts",
            ["organization_id"],
        )

    # ── account_audit_log ───────────────────────────────────────────
    if "account_audit_log" not in existing:
        op.create_table(
            "account_audit_log",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "account_id",
                UUID(as_uuid=True),
                sa.ForeignKey("accounts.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("action", sa.String(20), nullable=False),
            sa.Column("user_id", sa.String(100), nullable=False, index=True),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
                index=True,
            ),
            sa.Column("changes", JSONB, nullable=False),
            sa.Column("audit_metadata", JSONB, nullable=True),
        )

    # ── payment_entries ────────────────────────────────────────────
    if "payment_entries" not in existing:
        conn.execute(
            sa.text("""
            CREATE TABLE payment_entries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL,
                payment_type payment_type NOT NULL,
                party_id UUID NOT NULL,
                amount NUMERIC(15,2) NOT NULL,
                currency_code VARCHAR(3) NOT NULL DEFAULT 'USD',
                payment_date TIMESTAMPTZ NOT NULL,
                payment_mode payment_mode NOT NULL,
                reference_no VARCHAR(100),
                status payment_status NOT NULL DEFAULT 'Draft',
                source payment_source NOT NULL DEFAULT 'Manual',
                gateway_transaction_id VARCHAR(200),
                receipt_number VARCHAR(50) UNIQUE,
                cancellation_reason TEXT,
                cancelled_by UUID,
                cancelled_at TIMESTAMPTZ,
                created_by UUID NOT NULL,
                updated_by UUID NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_pe_amount CHECK (amount > 0),
                CONSTRAINT chk_pe_reference CHECK (
                    (payment_mode IN ('Check','Bank_Transfer') AND reference_no IS NOT NULL)
                    OR payment_mode = 'Cash'
                ),
                CONSTRAINT chk_pe_gateway CHECK (
                    (source IN ('Stripe','Razorpay') AND gateway_transaction_id IS NOT NULL)
                    OR source = 'Manual'
                )
            )
        """)
        )
        conn.execute(
            sa.text("CREATE INDEX idx_pe_org_id ON payment_entries (organization_id)")
        )
        conn.execute(sa.text("CREATE INDEX idx_pe_party ON payment_entries (party_id)"))
        conn.execute(
            sa.text(
                "CREATE INDEX idx_pe_status ON payment_entries (organization_id, status)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX idx_pe_date ON payment_entries (organization_id, payment_date)"
            )
        )
        conn.execute(
            sa.text("CREATE INDEX idx_pe_reference ON payment_entries (reference_no)")
        )
        conn.execute(
            sa.text("CREATE INDEX idx_pe_receipt ON payment_entries (receipt_number)")
        )

    # ── payment_references ──────────────────────────────────────────
    if "payment_references" not in existing:
        op.create_table(
            "payment_references",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "organization_id", UUID(as_uuid=True), nullable=False, index=True
            ),
            sa.Column(
                "payment_id",
                UUID(as_uuid=True),
                sa.ForeignKey("payment_entries.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "invoice_id",
                UUID(as_uuid=True),
                sa.ForeignKey("invoices.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("allocated_amount", sa.Numeric(15, 2), nullable=False),
            sa.Column(
                "exchange_rate", sa.Numeric(15, 6), nullable=True, server_default="1.0"
            ),
            sa.Column(
                "allocated_amount_invoice_currency", sa.Numeric(15, 2), nullable=True
            ),
            sa.Column("created_by", UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.UniqueConstraint(
                "payment_id",
                "invoice_id",
                name="unique_payment_references_payment_invoice",
            ),
        )

    # ── payment_audit_log ───────────────────────────────────────────
    if "payment_audit_log" not in existing:
        op.create_table(
            "payment_audit_log",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "organization_id", UUID(as_uuid=True), nullable=False, index=True
            ),
            sa.Column(
                "payment_id",
                UUID(as_uuid=True),
                sa.ForeignKey("payment_entries.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("action", sa.String(30), nullable=False),
            sa.Column("user_id", UUID(as_uuid=True), nullable=False),
            sa.Column("old_values", JSONB, nullable=True),
            sa.Column("new_values", JSONB, nullable=True),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
        )

    # ── bank_accounts ───────────────────────────────────────────────
    if "bank_accounts" not in existing:
        op.create_table(
            "bank_accounts",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "organization_id", UUID(as_uuid=True), nullable=False, index=True
            ),
            sa.Column("gl_account_id", UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("bank_name", sa.String(100), nullable=False),
            sa.Column("account_holder_name", sa.String(200), nullable=False),
            sa.Column("account_number", sa.String(50), nullable=False),
            sa.Column("iban", sa.String(34), nullable=True),
            sa.Column("swift_code", sa.String(11), nullable=True),
            sa.Column("routing_number", sa.String(20), nullable=True),
            sa.Column("branch_name", sa.String(100), nullable=True),
            sa.Column("branch_code", sa.String(20), nullable=True),
            sa.Column("sort_code", sa.String(10), nullable=True),
            sa.Column("bsb_number", sa.String(10), nullable=True),
            sa.Column("account_type", sa.String(50), nullable=True),
            sa.Column("account_purpose", sa.String(50), nullable=True),
            sa.Column(
                "is_primary", sa.Boolean(), nullable=False, server_default="false"
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("online_banking_enabled", sa.Boolean(), server_default="false"),
            sa.Column("mobile_banking_enabled", sa.Boolean(), server_default="false"),
            sa.Column("wire_transfer_enabled", sa.Boolean(), server_default="false"),
            sa.Column("ach_enabled", sa.Boolean(), server_default="false"),
            sa.Column("daily_transfer_limit", sa.Numeric(15, 2), nullable=True),
            sa.Column("monthly_transfer_limit", sa.Numeric(15, 2), nullable=True),
            sa.Column("requires_dual_approval", sa.Boolean(), server_default="false"),
            sa.Column("bank_api_enabled", sa.Boolean(), server_default="false"),
            sa.Column("bank_api_credentials_id", UUID(as_uuid=True), nullable=True),
            sa.Column("last_sync_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sync_frequency", sa.String(20), server_default="'manual'"),
            sa.Column("created_by", sa.String(100), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column("updated_by", sa.String(100), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.ForeignKeyConstraint(
                ["gl_account_id"],
                ["accounts.id"],
                name="fk_bank_accounts_gl_account",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("organization_id", "iban", name="unique_iban_per_org"),
        )
        op.create_index(
            "idx_bank_accounts_iban",
            "bank_accounts",
            ["iban"],
            postgresql_where=sa.text("iban IS NOT NULL"),
        )
        op.create_index(
            "idx_bank_accounts_active",
            "bank_accounts",
            ["is_active"],
            postgresql_where=sa.text("is_active = TRUE"),
        )
        op.create_index(
            "idx_bank_accounts_primary",
            "bank_accounts",
            ["is_primary"],
            postgresql_where=sa.text("is_primary = TRUE"),
        )

    # ── bank_account_history ────────────────────────────────────────
    if "bank_account_history" not in existing:
        op.create_table(
            "bank_account_history",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "bank_account_id", UUID(as_uuid=True), nullable=False, index=True
            ),
            sa.Column("action_type", sa.String(50), nullable=False, index=True),
            sa.Column("old_values", JSONB, nullable=True),
            sa.Column("new_values", JSONB, nullable=True),
            sa.Column("changed_by", sa.String(100), nullable=False),
            sa.Column(
                "changed_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["bank_account_id"],
                ["bank_accounts.id"],
                name="fk_bank_account_history_bank_account",
            ),
        )

    print("✅ Migration 019: All missing account/payment tables created")


def downgrade() -> None:
    conn = op.get_bind()
    existing = _existing(conn)

    for tbl in [
        "bank_account_history",
        "bank_accounts",
        "payment_audit_log",
        "payment_references",
        "payment_entries",
        "account_audit_log",
        "default_accounts",
        "account_balances",
        "accounts",
    ]:
        if tbl in existing:
            conn.execute(sa.text(f"DROP TABLE {tbl} CASCADE"))

    for enum in [
        "payment_audit_action",
        "payment_source",
        "payment_status",
        "payment_mode",
        "payment_type",
    ]:
        conn.execute(sa.text(f"DROP TYPE IF EXISTS {enum}"))
