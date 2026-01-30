-- ===========================================
-- Core Service - Phase 4, 5, 6, 7 Tables
-- ===========================================
-- Phase 4: Quality (templates, parameters, inspections, readings)
-- Phase 5: Pick lists, delivery notes, purchase receipts
-- Phase 6: Landed cost vouchers
-- Phase 7: Invoices, payments, journal entries
--
-- Prerequisites: 01_create_enums.sql, 02_create_foundation_tables.sql,
--                02_phase2_phase3_tables_and_seed.sql (items, warehouses, etc.)
--
-- Usage: psql -U horizon_user -d core_db -f 03_phase4_phase7_tables.sql

\c core_db;

\echo '============================================='
\echo 'Phase 4: Quality Management Tables'
\echo '============================================='

-- Quality Inspection Templates
CREATE TABLE IF NOT EXISTS quality_inspection_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(100) NOT NULL,
    description TEXT,
    item_id UUID,
    item_group_id UUID,
    inspection_type inspectiontype NOT NULL DEFAULT 'incoming',
    is_active BOOLEAN DEFAULT TRUE,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_qit_item FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL,
    CONSTRAINT fk_qit_item_group FOREIGN KEY (item_group_id) REFERENCES item_groups(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_quality_inspection_templates_organization_id ON quality_inspection_templates(organization_id);
CREATE INDEX IF NOT EXISTS ix_quality_inspection_templates_code ON quality_inspection_templates(organization_id, code);

-- Quality Inspection Parameters (child of template)
CREATE TABLE IF NOT EXISTS quality_inspection_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    template_id UUID NOT NULL,
    parameter_name VARCHAR(255) NOT NULL,
    reading_type readingtype NOT NULL DEFAULT 'numeric',
    numeric_min NUMERIC(15,4),
    numeric_max NUMERIC(15,4),
    uom VARCHAR(50),
    specification TEXT,
    sort_order INTEGER DEFAULT 0,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_qip_template FOREIGN KEY (template_id) REFERENCES quality_inspection_templates(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_quality_inspection_parameters_organization_id ON quality_inspection_parameters(organization_id);
CREATE INDEX IF NOT EXISTS ix_quality_inspection_parameters_template_id ON quality_inspection_parameters(template_id);

-- Quality Inspections (header)
CREATE TABLE IF NOT EXISTS quality_inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    inspection_no VARCHAR(100) NOT NULL,
    item_id UUID NOT NULL,
    template_id UUID,
    batch_no VARCHAR(100),
    serial_no VARCHAR(100),
    warehouse_id UUID,
    inspection_type inspectiontype NOT NULL DEFAULT 'incoming',
    status inspectionstatus NOT NULL DEFAULT 'pending',
    inspection_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reference_type VARCHAR(50),
    reference_id UUID,
    remarks TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_qi_item FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_qi_template FOREIGN KEY (template_id) REFERENCES quality_inspection_templates(id) ON DELETE SET NULL,
    CONSTRAINT fk_qi_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses_extended(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_quality_inspections_organization_id ON quality_inspections(organization_id);
CREATE INDEX IF NOT EXISTS ix_quality_inspections_inspection_no ON quality_inspections(organization_id, inspection_no);
CREATE INDEX IF NOT EXISTS ix_quality_inspections_item_id ON quality_inspections(item_id);
CREATE INDEX IF NOT EXISTS ix_quality_inspections_status ON quality_inspections(status);

-- Quality Inspection Readings (child of inspection)
CREATE TABLE IF NOT EXISTS quality_inspection_readings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    inspection_id UUID NOT NULL,
    parameter_id UUID NOT NULL,
    reading_value_numeric NUMERIC(15,4),
    reading_value_text TEXT,
    reading_value_pass_fail BOOLEAN,
    result VARCHAR(50),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_qir_inspection FOREIGN KEY (inspection_id) REFERENCES quality_inspections(id) ON DELETE CASCADE,
    CONSTRAINT fk_qir_parameter FOREIGN KEY (parameter_id) REFERENCES quality_inspection_parameters(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_quality_inspection_readings_organization_id ON quality_inspection_readings(organization_id);
CREATE INDEX IF NOT EXISTS ix_quality_inspection_readings_inspection_id ON quality_inspection_readings(inspection_id);

\echo 'Phase 5: Order Processing Tables'

-- Pick Lists (header)
CREATE TABLE IF NOT EXISTS pick_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    pick_list_no VARCHAR(100) NOT NULL,
    warehouse_id UUID NOT NULL,
    status pickliststatus NOT NULL DEFAULT 'draft',
    pick_date TIMESTAMP WITH TIME ZONE,
    reference_type VARCHAR(50),
    reference_id UUID,
    remarks TEXT,
    completed_at TIMESTAMP WITH TIME ZONE,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pl_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses_extended(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_pick_lists_organization_id ON pick_lists(organization_id);
CREATE INDEX IF NOT EXISTS ix_pick_lists_pick_list_no ON pick_lists(organization_id, pick_list_no);
CREATE INDEX IF NOT EXISTS ix_pick_lists_warehouse_id ON pick_lists(warehouse_id);

-- Pick List Items
CREATE TABLE IF NOT EXISTS pick_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    pick_list_id UUID NOT NULL,
    item_id UUID NOT NULL,
    warehouse_id UUID NOT NULL,
    qty NUMERIC(15,3) NOT NULL,
    picked_qty NUMERIC(15,3) DEFAULT 0,
    uom VARCHAR(50) NOT NULL,
    batch_no VARCHAR(100),
    serial_nos JSONB,
    sort_order INTEGER DEFAULT 0,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pli_pick_list FOREIGN KEY (pick_list_id) REFERENCES pick_lists(id) ON DELETE CASCADE,
    CONSTRAINT fk_pli_item FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_pli_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses_extended(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_pick_list_items_organization_id ON pick_list_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_pick_list_items_pick_list_id ON pick_list_items(pick_list_id);

-- Delivery Notes (header)
CREATE TABLE IF NOT EXISTS delivery_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    delivery_note_no VARCHAR(100) NOT NULL,
    customer_id UUID NOT NULL,
    delivery_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status documentstatus NOT NULL DEFAULT 'draft',
    warehouse_id UUID,
    pick_list_id UUID,
    reference_type VARCHAR(50),
    reference_id UUID,
    remarks TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dn_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    CONSTRAINT fk_dn_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses_extended(id) ON DELETE SET NULL,
    CONSTRAINT fk_dn_pick_list FOREIGN KEY (pick_list_id) REFERENCES pick_lists(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_delivery_notes_organization_id ON delivery_notes(organization_id);
CREATE INDEX IF NOT EXISTS ix_delivery_notes_delivery_note_no ON delivery_notes(organization_id, delivery_note_no);
CREATE INDEX IF NOT EXISTS ix_delivery_notes_customer_id ON delivery_notes(customer_id);

-- Delivery Note Items
CREATE TABLE IF NOT EXISTS delivery_note_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    delivery_note_id UUID NOT NULL,
    item_id UUID NOT NULL,
    qty NUMERIC(15,3) NOT NULL,
    uom VARCHAR(50) NOT NULL,
    rate NUMERIC(15,2),
    amount NUMERIC(15,2),
    warehouse_id UUID,
    batch_no VARCHAR(100),
    serial_nos JSONB,
    sort_order INTEGER DEFAULT 0,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dni_delivery_note FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes(id) ON DELETE CASCADE,
    CONSTRAINT fk_dni_item FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_dni_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses_extended(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_delivery_note_items_organization_id ON delivery_note_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_delivery_note_items_delivery_note_id ON delivery_note_items(delivery_note_id);

-- Purchase Receipts (header)
CREATE TABLE IF NOT EXISTS purchase_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    purchase_receipt_no VARCHAR(100) NOT NULL,
    supplier_id UUID NOT NULL,
    receipt_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status documentstatus NOT NULL DEFAULT 'draft',
    warehouse_id UUID,
    reference_type VARCHAR(50),
    reference_id UUID,
    remarks TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pr_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
    CONSTRAINT fk_pr_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses_extended(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_purchase_receipts_organization_id ON purchase_receipts(organization_id);
CREATE INDEX IF NOT EXISTS ix_purchase_receipts_purchase_receipt_no ON purchase_receipts(organization_id, purchase_receipt_no);
CREATE INDEX IF NOT EXISTS ix_purchase_receipts_supplier_id ON purchase_receipts(supplier_id);

-- Purchase Receipt Items
CREATE TABLE IF NOT EXISTS purchase_receipt_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    purchase_receipt_id UUID NOT NULL,
    item_id UUID NOT NULL,
    qty NUMERIC(15,3) NOT NULL,
    uom VARCHAR(50) NOT NULL,
    rate NUMERIC(15,2),
    amount NUMERIC(15,2),
    warehouse_id UUID,
    batch_no VARCHAR(100),
    serial_nos JSONB,
    sort_order INTEGER DEFAULT 0,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pri_purchase_receipt FOREIGN KEY (purchase_receipt_id) REFERENCES purchase_receipts(id) ON DELETE CASCADE,
    CONSTRAINT fk_pri_item FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_pri_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses_extended(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_purchase_receipt_items_organization_id ON purchase_receipt_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_purchase_receipt_items_purchase_receipt_id ON purchase_receipt_items(purchase_receipt_id);

\echo 'Phase 6: Landed Cost Tables'

-- Landed Cost Vouchers (header)
CREATE TABLE IF NOT EXISTS landed_cost_vouchers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    voucher_no VARCHAR(100) NOT NULL,
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status documentstatus NOT NULL DEFAULT 'draft',
    remarks TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_landed_cost_vouchers_organization_id ON landed_cost_vouchers(organization_id);
CREATE INDEX IF NOT EXISTS ix_landed_cost_vouchers_voucher_no ON landed_cost_vouchers(organization_id, voucher_no);

-- Landed Cost - Purchase Receipts (link)
CREATE TABLE IF NOT EXISTS landed_cost_purchase_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    landed_cost_voucher_id UUID NOT NULL,
    purchase_receipt_id UUID NOT NULL,
    amount NUMERIC(15,2) DEFAULT 0,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lcpr_voucher FOREIGN KEY (landed_cost_voucher_id) REFERENCES landed_cost_vouchers(id) ON DELETE CASCADE,
    CONSTRAINT fk_lcpr_purchase_receipt FOREIGN KEY (purchase_receipt_id) REFERENCES purchase_receipts(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_landed_cost_purchase_receipts_organization_id ON landed_cost_purchase_receipts(organization_id);
CREATE INDEX IF NOT EXISTS ix_landed_cost_purchase_receipts_voucher_id ON landed_cost_purchase_receipts(landed_cost_voucher_id);

-- Landed Cost Items (allocation to items)
CREATE TABLE IF NOT EXISTS landed_cost_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    landed_cost_voucher_id UUID NOT NULL,
    purchase_receipt_id UUID,
    purchase_receipt_item_id UUID,
    item_id UUID NOT NULL,
    qty NUMERIC(15,3) NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lci_voucher FOREIGN KEY (landed_cost_voucher_id) REFERENCES landed_cost_vouchers(id) ON DELETE CASCADE,
    CONSTRAINT fk_lci_purchase_receipt FOREIGN KEY (purchase_receipt_id) REFERENCES purchase_receipts(id) ON DELETE SET NULL,
    CONSTRAINT fk_lci_item FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_landed_cost_items_organization_id ON landed_cost_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_landed_cost_items_voucher_id ON landed_cost_items(landed_cost_voucher_id);

-- Landed Cost Taxes and Charges
CREATE TABLE IF NOT EXISTS landed_cost_taxes_and_charges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    landed_cost_voucher_id UUID NOT NULL,
    description VARCHAR(255),
    amount NUMERIC(15,2) NOT NULL DEFAULT 0,
    account_id UUID,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lctc_voucher FOREIGN KEY (landed_cost_voucher_id) REFERENCES landed_cost_vouchers(id) ON DELETE CASCADE,
    CONSTRAINT fk_lctc_account FOREIGN KEY (account_id) REFERENCES chart_of_accounts(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_landed_cost_taxes_and_charges_organization_id ON landed_cost_taxes_and_charges(organization_id);
CREATE INDEX IF NOT EXISTS ix_landed_cost_taxes_and_charges_voucher_id ON landed_cost_taxes_and_charges(landed_cost_voucher_id);

\echo 'Phase 7: Billing Tables'

-- Invoices (header)
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    invoice_no VARCHAR(100) NOT NULL,
    invoice_type invoicetype NOT NULL,
    party_id UUID NOT NULL,
    party_type VARCHAR(20) NOT NULL,
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date TIMESTAMP WITH TIME ZONE,
    status invoicestatus NOT NULL DEFAULT 'draft',
    grand_total NUMERIC(15,2) DEFAULT 0,
    outstanding_amount NUMERIC(15,2) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'INR',
    reference_type VARCHAR(50),
    reference_id UUID,
    remarks TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_invoices_organization_id ON invoices(organization_id);
CREATE INDEX IF NOT EXISTS ix_invoices_invoice_no ON invoices(organization_id, invoice_no);
CREATE INDEX IF NOT EXISTS ix_invoices_party ON invoices(party_id, party_type);
CREATE INDEX IF NOT EXISTS ix_invoices_status ON invoices(status);

-- Invoice Items
CREATE TABLE IF NOT EXISTS invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    invoice_id UUID NOT NULL,
    item_id UUID,
    item_code VARCHAR(100),
    item_name VARCHAR(255),
    qty NUMERIC(15,3) NOT NULL,
    uom VARCHAR(50) NOT NULL,
    rate NUMERIC(15,2),
    amount NUMERIC(15,2),
    sort_order INTEGER DEFAULT 0,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invi_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    CONSTRAINT fk_invi_item FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_invoice_items_organization_id ON invoice_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_invoice_items_invoice_id ON invoice_items(invoice_id);

-- Payments (header)
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    payment_no VARCHAR(100) NOT NULL,
    payment_type paymenttype NOT NULL,
    party_id UUID NOT NULL,
    party_type VARCHAR(20) NOT NULL,
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount NUMERIC(15,2) NOT NULL,
    status paymentstatus NOT NULL DEFAULT 'pending',
    payment_method paymentmethod,
    reference_no VARCHAR(100),
    remarks TEXT,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_payments_organization_id ON payments(organization_id);
CREATE INDEX IF NOT EXISTS ix_payments_payment_no ON payments(organization_id, payment_no);
CREATE INDEX IF NOT EXISTS ix_payments_party ON payments(party_id, party_type);

-- Payment Allocations
CREATE TABLE IF NOT EXISTS payment_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    payment_id UUID NOT NULL,
    invoice_id UUID NOT NULL,
    allocated_amount NUMERIC(15,2) NOT NULL,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pa_payment FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE,
    CONSTRAINT fk_pa_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_payment_allocations_organization_id ON payment_allocations(organization_id);
CREATE INDEX IF NOT EXISTS ix_payment_allocations_payment_id ON payment_allocations(payment_id);
CREATE INDEX IF NOT EXISTS ix_payment_allocations_invoice_id ON payment_allocations(invoice_id);

-- Journal Entries (header)
CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    entry_no VARCHAR(100) NOT NULL,
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status journalstatus NOT NULL DEFAULT 'draft',
    voucher_type VARCHAR(50),
    reference_type VARCHAR(50),
    reference_id UUID,
    total_debit NUMERIC(15,2) DEFAULT 0,
    total_credit NUMERIC(15,2) DEFAULT 0,
    remarks TEXT,
    posted_at TIMESTAMP WITH TIME ZONE,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_journal_entries_organization_id ON journal_entries(organization_id);
CREATE INDEX IF NOT EXISTS ix_journal_entries_entry_no ON journal_entries(organization_id, entry_no);
CREATE INDEX IF NOT EXISTS ix_journal_entries_posting_date ON journal_entries(posting_date);

-- Journal Entry Lines
CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    journal_entry_id UUID NOT NULL,
    account_id UUID NOT NULL,
    debit NUMERIC(15,2) DEFAULT 0,
    credit NUMERIC(15,2) DEFAULT 0,
    against_account_id UUID,
    reference_type VARCHAR(50),
    reference_id UUID,
    remarks TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_jel_journal_entry FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
    CONSTRAINT fk_jel_account FOREIGN KEY (account_id) REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    CONSTRAINT fk_jel_against_account FOREIGN KEY (against_account_id) REFERENCES chart_of_accounts(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_journal_entry_lines_organization_id ON journal_entry_lines(organization_id);
CREATE INDEX IF NOT EXISTS ix_journal_entry_lines_journal_entry_id ON journal_entry_lines(journal_entry_id);

\echo 'Phase 4, 5, 6, 7 tables created successfully!'
