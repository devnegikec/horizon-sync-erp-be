"""Create core tables baseline - all tables managed by SQLAlchemy create_all

Revision ID: 041_create_core_tables_baseline
Revises: 040_add_feature_flags_table
Create Date: 2026-04-29

This migration creates all tables that were previously only created by
SQLAlchemy's create_all() at app startup. On a fresh DB, Alembic runs
migrations before the app starts, so these tables don't exist when later
migrations try to ALTER them.

All CREATE TABLE statements use IF NOT EXISTS so this is safe on existing DBs.
All enum CREATE TYPE statements use DO $$ BEGIN ... EXCEPTION WHEN duplicate_object
so they are also idempotent.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '041_create_core_tables_baseline'
down_revision = '040_add_feature_flags_table'
branch_labels = None
depends_on = None


def _create_enum_if_not_exists(conn, name: str, values: list[str]) -> None:
    vals = ", ".join(f"'{v}'" for v in values)
    conn.execute(sa.text(f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({vals});
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """))


def upgrade() -> None:
    conn = op.get_bind()

    # ── Enums ──────────────────────────────────────────────────────
    _create_enum_if_not_exists(conn, 'itemtype', ['stock', 'non_stock', 'service', 'fixed_asset'])
    _create_enum_if_not_exists(conn, 'itemstatus', ['active', 'inactive', 'discontinued'])
    _create_enum_if_not_exists(conn, 'valuationmethod', ['fifo', 'lifo', 'moving_average', 'standard'])
    _create_enum_if_not_exists(conn, 'warehousetype', ['warehouse', 'store', 'virtual', 'transit'])
    _create_enum_if_not_exists(conn, 'customerstatus', ['active', 'inactive', 'blocked'])
    _create_enum_if_not_exists(conn, 'supplierstatus', ['active', 'inactive', 'blocked'])
    _create_enum_if_not_exists(conn, 'invoicetype', [
        'sales', 'purchase', 'subscription', 'setup_fee', 'overage', 'addon', 'credit_adjustment'
    ])
    _create_enum_if_not_exists(conn, 'invoicestatus', [
        'draft', 'pending', 'paid', 'partial', 'overdue', 'cancelled'
    ])
    _create_enum_if_not_exists(conn, 'billingcycle', ['monthly', 'quarterly', 'yearly'])
    _create_enum_if_not_exists(conn, 'journalstatus', ['draft', 'posted', 'cancelled'])
    _create_enum_if_not_exists(conn, 'documentstatus', ['draft', 'submitted', 'cancelled'])
    _create_enum_if_not_exists(conn, 'batchstatus', ['active', 'expired', 'consumed'])
    _create_enum_if_not_exists(conn, 'stockentrytype', [
        'material_receipt', 'material_issue', 'material_transfer',
        'manufacture', 'repack', 'send_to_subcontractor'
    ])
    _create_enum_if_not_exists(conn, 'stockentrystatus', ['draft', 'submitted', 'cancelled'])
    _create_enum_if_not_exists(conn, 'movementtype', ['in', 'out', 'transfer', 'adjustment'])
    _create_enum_if_not_exists(conn, 'quotationstatus', ['draft', 'sent', 'accepted', 'rejected', 'expired'])
    _create_enum_if_not_exists(conn, 'salesorderstatus', [
        'draft', 'confirmed', 'partially_delivered', 'delivered', 'closed', 'cancelled'
    ])
    _create_enum_if_not_exists(conn, 'pickliststatus', ['draft', 'in_progress', 'completed', 'cancelled'])
    _create_enum_if_not_exists(conn, 'materialrequesttype', ['purchase', 'transfer', 'issue'])
    _create_enum_if_not_exists(conn, 'materialrequestpriority', ['low', 'medium', 'high', 'urgent'])
    _create_enum_if_not_exists(conn, 'materialrequeststatus', [
        'draft', 'submitted', 'partially_quoted', 'fully_quoted', 'cancelled'
    ])
    _create_enum_if_not_exists(conn, 'rfqstatus', [
        'draft', 'sent', 'partially_responded', 'fully_responded', 'closed'
    ])
    _create_enum_if_not_exists(conn, 'purchaseorderstatus', [
        'draft', 'submitted', 'partially_received', 'fully_received', 'closed', 'cancelled'
    ])
    _create_enum_if_not_exists(conn, 'defaultaccounttransactiontype', [
        'accounts_receivable', 'sales_revenue', 'accounts_payable', 'purchase_expense',
        'inventory_asset', 'cost_of_goods_sold', 'cash', 'bank', 'checks_received',
        'demand_draft', 'tax_payable', 'tax_receivable', 'discount_given', 'discount_received',
        'freight_expense', 'shipping_charges', 'inventory_purchase', 'inventory_sale',
        'sales_invoice', 'purchase_invoice'
    ])

    # ── item_groups ────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS item_groups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            code VARCHAR(50),
            description TEXT,
            parent_id UUID REFERENCES item_groups(id),
            is_active BOOLEAN DEFAULT TRUE,
            extra_data JSONB,
            created_by UUID,
            updated_by UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """))

    # ── tax_templates ──────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS tax_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            template_code VARCHAR(100) NOT NULL,
            template_name VARCHAR(255) NOT NULL,
            description TEXT,
            tax_category VARCHAR(50) NOT NULL,
            is_default BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            applicability_rules JSONB,
            extra_data JSONB,
            created_by UUID,
            updated_by UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """))

    # ── tax_rules ──────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS tax_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tax_template_id UUID NOT NULL REFERENCES tax_templates(id) ON DELETE CASCADE,
            rule_name VARCHAR(255) NOT NULL,
            tax_type VARCHAR(100) NOT NULL,
            description TEXT,
            tax_rate NUMERIC(5,2) NOT NULL,
            account_head_id UUID NOT NULL,
            is_compound BOOLEAN DEFAULT FALSE,
            sequence INTEGER NOT NULL,
            applicability_conditions JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))

    # ── items ──────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            item_code VARCHAR(100) NOT NULL,
            item_name VARCHAR(255) NOT NULL,
            description TEXT,
            item_group_id UUID REFERENCES item_groups(id),
            item_type itemtype DEFAULT 'stock',
            uom VARCHAR(50) DEFAULT 'Nos',
            maintain_stock BOOLEAN DEFAULT TRUE,
            valuation_method valuationmethod DEFAULT 'fifo',
            allow_negative_stock BOOLEAN DEFAULT FALSE,
            has_variants BOOLEAN DEFAULT FALSE,
            variant_of UUID REFERENCES items(id),
            variant_attributes JSONB,
            has_batch_no BOOLEAN DEFAULT FALSE,
            has_serial_no BOOLEAN DEFAULT FALSE,
            batch_number_series VARCHAR(100),
            serial_number_series VARCHAR(100),
            standard_rate NUMERIC(15,2) DEFAULT 0,
            valuation_rate NUMERIC(15,2) DEFAULT 0,
            enable_auto_reorder BOOLEAN DEFAULT FALSE,
            reorder_level INTEGER DEFAULT 0,
            reorder_qty INTEGER DEFAULT 0,
            min_order_qty INTEGER DEFAULT 1,
            max_order_qty INTEGER,
            weight_per_unit NUMERIC(10,3),
            weight_uom VARCHAR(50),
            inspection_required_before_purchase BOOLEAN DEFAULT FALSE,
            inspection_required_before_delivery BOOLEAN DEFAULT FALSE,
            quality_inspection_template UUID,
            sales_tax_template_id UUID REFERENCES tax_templates(id),
            purchase_tax_template_id UUID REFERENCES tax_templates(id),
            barcode VARCHAR(100),
            status itemstatus DEFAULT 'active',
            image_url VARCHAR(500),
            images JSONB,
            tags JSONB,
            custom_fields JSONB,
            extra_data JSONB,
            created_by UUID,
            updated_by UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """))

    # ── customers ─────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS customers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            customer_name VARCHAR(255) NOT NULL,
            customer_code VARCHAR(50) NOT NULL,
            email VARCHAR(255),
            phone VARCHAR(50),
            address TEXT,
            address_line1 VARCHAR(255),
            address_line2 VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(100),
            postal_code VARCHAR(20),
            country VARCHAR(100),
            tax_number VARCHAR(50),
            status customerstatus DEFAULT 'active',
            credit_limit NUMERIC(15,2) DEFAULT 0,
            outstanding_balance NUMERIC(15,2) DEFAULT 0,
            tags JSONB,
            custom_fields JSONB,
            extra_data JSONB,
            created_by UUID,
            updated_by UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """))

    # ── suppliers ─────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            supplier_name VARCHAR(255) NOT NULL,
            supplier_code VARCHAR(50) NOT NULL,
            email VARCHAR(255),
            phone VARCHAR(50),
            address TEXT,
            address_line1 VARCHAR(255),
            address_line2 VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(100),
            postal_code VARCHAR(20),
            country VARCHAR(100),
            tax_number VARCHAR(50),
            status supplierstatus DEFAULT 'active',
            payment_terms INTEGER DEFAULT 30,
            tags JSONB,
            custom_fields JSONB,
            extra_data JSONB,
            created_by UUID,
            updated_by UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """))

    # ── invoices ──────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS invoices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            invoice_no VARCHAR(100) NOT NULL,
            invoice_type VARCHAR(50) NOT NULL,
            party_id UUID,
            party_type VARCHAR(50),
            posting_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            due_date TIMESTAMPTZ,
            status VARCHAR(50) DEFAULT 'draft' NOT NULL,
            grand_total NUMERIC(15,2) DEFAULT 0,
            outstanding_amount NUMERIC(15,2) DEFAULT 0,
            currency VARCHAR(10) DEFAULT 'USD',
            reference_type VARCHAR(100),
            reference_id UUID,
            remarks TEXT,
            submitted_at TIMESTAMPTZ,
            extra_data JSONB,
            created_by UUID,
            updated_by UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            net_total NUMERIC(15,2) DEFAULT 0,
            total_tax NUMERIC(15,2) DEFAULT 0,
            total_charges NUMERIC(15,2) DEFAULT 0,
            discount_type VARCHAR(20) DEFAULT 'percentage',
            discount_value NUMERIC(15,2) DEFAULT 0,
            billing_cycle VARCHAR(20),
            subscription_period_start TIMESTAMPTZ,
            subscription_period_end TIMESTAMPTZ,
            seat_count INTEGER,
            credit_usage NUMERIC(15,2)
        )
    """))

    # ── invoice_items ─────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
            item_id UUID REFERENCES items(id) ON DELETE SET NULL,
            item_code VARCHAR(100),
            item_name VARCHAR(255),
            qty NUMERIC(15,3) NOT NULL,
            uom VARCHAR(50) NOT NULL,
            rate NUMERIC(15,2),
            amount NUMERIC(15,2),
            sort_order INTEGER DEFAULT 0,
            tax_template_id UUID REFERENCES tax_templates(id) ON DELETE SET NULL,
            tax_rate NUMERIC(5,2) DEFAULT 0,
            tax_amount NUMERIC(15,2) DEFAULT 0,
            discount_type VARCHAR(20) DEFAULT 'percentage',
            discount_value NUMERIC(15,2) DEFAULT 0,
            discount_amount NUMERIC(15,2) DEFAULT 0,
            total_amount NUMERIC(15,2) DEFAULT 0,
            extra_data JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))

    # ── warehouses_extended ───────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS warehouses_extended (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            code VARCHAR(50) NOT NULL,
            description TEXT,
            parent_warehouse_id UUID REFERENCES warehouses_extended(id),
            warehouse_type warehousetype DEFAULT 'warehouse',
            address_line1 VARCHAR(255),
            address_line2 VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(100),
            postal_code VARCHAR(20),
            country VARCHAR(100),
            contact_name VARCHAR(255),
            contact_phone VARCHAR(50),
            contact_email VARCHAR(255),
            total_capacity INTEGER,
            capacity_uom VARCHAR(50),
            stock_account_id UUID,
            is_active BOOLEAN DEFAULT TRUE,
            is_default BOOLEAN DEFAULT FALSE,
            extra_data JSONB,
            created_by UUID,
            updated_by UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """))

    # ── payment_references (with FK to invoices now that it exists) ─
    # Drop and recreate only if the FK is missing
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'payment_references_invoice_id_fkey'
                AND table_name = 'payment_references'
            ) THEN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'payment_references') THEN
                    ALTER TABLE payment_references
                        ADD CONSTRAINT payment_references_invoice_id_fkey
                        FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE;
                END IF;
            END IF;
        END $$;
    """))

    # ── Indexes ────────────────────────────────────────────────────
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS ix_invoices_org ON invoices (organization_id)",
        "CREATE INDEX IF NOT EXISTS ix_invoices_status ON invoices (organization_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_invoices_posting_date ON invoices (organization_id, posting_date)",
        "CREATE INDEX IF NOT EXISTS ix_invoice_items_invoice ON invoice_items (invoice_id)",
        "CREATE INDEX IF NOT EXISTS ix_invoice_items_org ON invoice_items (organization_id)",
        "CREATE INDEX IF NOT EXISTS ix_items_org ON items (organization_id)",
        "CREATE INDEX IF NOT EXISTS ix_items_code ON items (organization_id, item_code)",
        "CREATE INDEX IF NOT EXISTS ix_customers_org ON customers (organization_id)",
        "CREATE INDEX IF NOT EXISTS ix_customers_code ON customers (organization_id, customer_code)",
        "CREATE INDEX IF NOT EXISTS ix_suppliers_org ON suppliers (organization_id)",
        "CREATE INDEX IF NOT EXISTS ix_suppliers_code ON suppliers (organization_id, supplier_code)",
        "CREATE INDEX IF NOT EXISTS ix_tax_templates_org ON tax_templates (organization_id)",
        "CREATE INDEX IF NOT EXISTS ix_warehouses_extended_org ON warehouses_extended (organization_id)",
        "CREATE INDEX IF NOT EXISTS ix_invoices_billing_cycle ON invoices (billing_cycle)",
        "CREATE INDEX IF NOT EXISTS ix_invoices_subscription_period ON invoices (subscription_period_start, subscription_period_end)",
    ]:
        conn.execute(sa.text(idx_sql))


def downgrade() -> None:
    # These tables may be in use; downgrade is a no-op to avoid data loss
    pass
