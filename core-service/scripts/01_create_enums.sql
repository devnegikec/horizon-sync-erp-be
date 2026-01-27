-- ===========================================
-- Core Service - Create Enum Types
-- ===========================================
-- This script creates all enum types for core-service
-- Run this FIRST before creating any tables
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/01_create_enums.sql
--   OR
--   psql -U horizon_user -d core_db -f 01_create_enums.sql

-- Connect to core_db (if running manually)
\c core_db;

-- ===========================================
-- Drop existing types (if any) to start fresh
-- ===========================================
DROP TYPE IF EXISTS itemtype CASCADE;
DROP TYPE IF EXISTS itemstatus CASCADE;
DROP TYPE IF EXISTS valuationmethod CASCADE;
DROP TYPE IF EXISTS documentstatus CASCADE;
DROP TYPE IF EXISTS warehousetype CASCADE;
DROP TYPE IF EXISTS stockentrytype CASCADE;
DROP TYPE IF EXISTS stockentrystatus CASCADE;
DROP TYPE IF EXISTS movementtype CASCADE;
DROP TYPE IF EXISTS batchstatus CASCADE;
DROP TYPE IF EXISTS inspectiontype CASCADE;
DROP TYPE IF EXISTS inspectionstatus CASCADE;
DROP TYPE IF EXISTS readingtype CASCADE;
DROP TYPE IF EXISTS customerstatus CASCADE;
DROP TYPE IF EXISTS supplierstatus CASCADE;
DROP TYPE IF EXISTS accounttype CASCADE;
DROP TYPE IF EXISTS invoicetype CASCADE;
DROP TYPE IF EXISTS invoicestatus CASCADE;
DROP TYPE IF EXISTS paymenttype CASCADE;
DROP TYPE IF EXISTS paymentstatus CASCADE;
DROP TYPE IF EXISTS paymentmethod CASCADE;
DROP TYPE IF EXISTS journalstatus CASCADE;
DROP TYPE IF EXISTS pickliststatus CASCADE;

-- ===========================================
-- INVENTORY ENUMS
-- ===========================================

-- Item Type
CREATE TYPE itemtype AS ENUM (
    'stock',
    'non_stock',
    'service',
    'fixed_asset'
);

-- Item Status
CREATE TYPE itemstatus AS ENUM (
    'active',
    'inactive',
    'discontinued'
);

-- Valuation Method
CREATE TYPE valuationmethod AS ENUM (
    'fifo',
    'lifo',
    'moving_average',
    'standard'
);

-- Document Status (for transactions)
CREATE TYPE documentstatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);

-- Warehouse Type
CREATE TYPE warehousetype AS ENUM (
    'warehouse',
    'store',
    'virtual',
    'transit'
);

-- Stock Entry Type
CREATE TYPE stockentrytype AS ENUM (
    'material_receipt',
    'material_issue',
    'material_transfer',
    'manufacture',
    'repack',
    'send_to_subcontractor'
);

-- Stock Entry Status
CREATE TYPE stockentrystatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);

-- Movement Type
CREATE TYPE movementtype AS ENUM (
    'in',
    'out',
    'transfer',
    'adjustment'
);

-- Batch Status
CREATE TYPE batchstatus AS ENUM (
    'active',
    'expired',
    'consumed'
);

-- ===========================================
-- QUALITY INSPECTION ENUMS
-- ===========================================

-- Inspection Type
CREATE TYPE inspectiontype AS ENUM (
    'incoming',
    'outgoing',
    'in_process'
);

-- Inspection Status
CREATE TYPE inspectionstatus AS ENUM (
    'pending',
    'accepted',
    'rejected'
);

-- Reading Type
CREATE TYPE readingtype AS ENUM (
    'numeric',
    'text',
    'pass_fail'
);

-- ===========================================
-- CUSTOMER/SUPPLIER ENUMS
-- ===========================================

-- Customer Status
CREATE TYPE customerstatus AS ENUM (
    'active',
    'inactive',
    'blocked'
);

-- Supplier Status
CREATE TYPE supplierstatus AS ENUM (
    'active',
    'inactive',
    'blocked'
);

-- ===========================================
-- ACCOUNTING/BILLING ENUMS
-- ===========================================

-- Account Type (Chart of Accounts)
CREATE TYPE accounttype AS ENUM (
    'asset',
    'liability',
    'equity',
    'income',
    'expense'
);

-- Invoice Type
CREATE TYPE invoicetype AS ENUM (
    'sales',
    'purchase'
);

-- Invoice Status
CREATE TYPE invoicestatus AS ENUM (
    'draft',
    'pending',
    'paid',
    'partial',
    'overdue',
    'cancelled'
);

-- Payment Type
CREATE TYPE paymenttype AS ENUM (
    'receive',
    'pay'
);

-- Payment Status
CREATE TYPE paymentstatus AS ENUM (
    'pending',
    'completed',
    'failed',
    'cancelled'
);

-- Payment Method
CREATE TYPE paymentmethod AS ENUM (
    'cash',
    'bank_transfer',
    'credit_card',
    'debit_card',
    'cheque',
    'upi',
    'other'
);

-- Journal Entry Status
CREATE TYPE journalstatus AS ENUM (
    'draft',
    'posted',
    'cancelled'
);

-- ===========================================
-- ORDER PROCESSING ENUMS
-- ===========================================

-- Pick List Status
CREATE TYPE pickliststatus AS ENUM (
    'draft',
    'in_progress',
    'completed',
    'cancelled'
);

-- ===========================================
-- Verification
-- ===========================================
SELECT 'All enum types created successfully!' AS status;

-- List all enum types
SELECT
    t.typname AS enum_name,
    string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS enum_values
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname IN (
    'itemtype', 'itemstatus', 'valuationmethod', 'documentstatus',
    'warehousetype', 'stockentrytype', 'stockentrystatus', 'movementtype',
    'batchstatus', 'inspectiontype', 'inspectionstatus', 'readingtype',
    'customerstatus', 'supplierstatus', 'accounttype', 'invoicetype',
    'invoicestatus', 'paymenttype', 'paymentstatus', 'paymentmethod',
    'journalstatus', 'pickliststatus'
)
GROUP BY t.typname
ORDER BY t.typname;
