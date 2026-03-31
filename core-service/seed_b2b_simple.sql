/*
 * B2B Billing Test Data Seed Script
 * 
 * Creates essential test data for B2B billing system:
 * - Organizations with B2B hierarchy
 * - Sample subscription invoices  
 * - Payment reminder configurations
 * - Payment entries and allocations
 * 
 * Run this within the core-service database:
 * docker compose exec postgres psql -U horizon_user -d core_db -f seed_b2b_simple.sql
 */

-- Use specific UUIDs for consistent testing
\set MASTER_ORG_ID '550e8400-e29b-41d4-a716-446655440001'
\set ACME_ORG_ID '550e8400-e29b-41d4-a716-446655440011'
\set TECH_ORG_ID '550e8400-e29b-41d4-a716-446655440012'
\set GLOBAL_ORG_ID '550e8400-e29b-41d4-a716-446655440013'
\set ADMIN_USER_ID '550e8400-e29b-41d4-a716-446655440099'

-- Clean up existing test data
DELETE FROM reminder_logs WHERE organization_id IN (:'ACME_ORG_ID', :'TECH_ORG_ID', :'GLOBAL_ORG_ID');
DELETE FROM reminder_configs WHERE organization_id IN (:'ACME_ORG_ID', :'TECH_ORG_ID', :'GLOBAL_ORG_ID');
DELETE FROM payment_references WHERE organization_id = :'MASTER_ORG_ID';
DELETE FROM payment_entries WHERE organization_id = :'MASTER_ORG_ID';
DELETE FROM invoice_items WHERE organization_id = :'MASTER_ORG_ID';
DELETE FROM invoices WHERE organization_id = :'MASTER_ORG_ID';

ECHO 'Starting B2B Test Data Seeding...';

-- 1. Create Essential Chart of Accounts
ECHO 'Creating Chart of Accounts...';
INSERT INTO accounts (
    id, organization_id, account_code, account_name, account_type,
    currency, status, is_posting_account, created_by, updated_by,
    created_at, updated_at
) VALUES 
    (gen_random_uuid(), :'MASTER_ORG_ID', '1110', 'Cash and Bank', 'ASSET', 'USD', 'ACTIVE', true, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW()),
    (gen_random_uuid(), :'MASTER_ORG_ID', '1120', 'Accounts Receivable', 'ASSET', 'USD', 'ACTIVE', true, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW()),
    (gen_random_uuid(), :'MASTER_ORG_ID', '4110', 'Subscription Revenue', 'REVENUE', 'USD', 'ACTIVE', true, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW()),
    (gen_random_uuid(), :'MASTER_ORG_ID', '4120', 'Professional Services', 'REVENUE', 'USD', 'ACTIVE', true, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW())
ON CONFLICT (organization_id, account_code) DO NOTHING;

-- 2. Create Bank Accounts
ECHO 'Creating Bank Accounts...';
INSERT INTO bank_accounts (
    id, organization_id, account_name, account_number, bank_name,
    routing_number, account_type, currency, is_default,
    created_by, updated_by, created_at, updated_at
) VALUES 
    (gen_random_uuid(), :'MASTER_ORG_ID', 'HorizonSync Primary Checking', '123456789', 'Chase Business', '021000021', 'checking', 'USD', true, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW()),
    (gen_random_uuid(), :'MASTER_ORG_ID', 'HorizonSync Savings', '987654321', 'Wells Fargo Business', '121042882', 'savings', 'USD', false, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW())
ON CONFLICT (organization_id, account_number) DO NOTHING;

-- 3. Create B2B Subscription Invoices
ECHO 'Creating B2B Subscription Invoices...';

-- Acme Corp Invoices (3 months)
INSERT INTO invoices (
    id, organization_id, invoice_no, invoice_type, party_id, 
    posting_date, due_date, status, grand_total, outstanding_amount,
    net_total, total_tax, billing_cycle, subscription_period_start, 
    subscription_period_end, seat_count, created_by, updated_by, created_at, updated_at
) VALUES
    -- Current month - Outstanding
    (gen_random_uuid(), :'MASTER_ORG_ID', 'INV-ACME-202603', 'subscription', :'ACME_ORG_ID', 
     '2026-03-01', '2026-03-31', 'outstanding', 549.99, 549.99, 
     499.99, 50.00, 'monthly', '2026-03-01', '2026-03-31', 
     25, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW()),
    
    -- Last month - Partial paid  
    (gen_random_uuid(), :'MASTER_ORG_ID', 'INV-ACME-202602', 'subscription', :'ACME_ORG_ID',
     '2026-02-01', '2026-02-28', 'partial_paid', 549.99, 164.99,
     499.99, 50.00, 'monthly', '2026-02-01', '2026-02-28',
     25, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW()),
    
    -- Two months ago - Fully paid
    (gen_random_uuid(), :'MASTER_ORG_ID', 'INV-ACME-202601', 'subscription', :'ACME_ORG_ID',
     '2026-01-01', '2026-01-31', 'paid', 549.99, 0,
     499.99, 50.00, 'monthly', '2026-01-01', '2026-01-31', 
     25, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW()),

-- TechStart Invoices (3 months)
    -- Current month - Outstanding
    (gen_random_uuid(), :'MASTER_ORG_ID', 'INV-TECH-202603', 'subscription', :'TECH_ORG_ID',
     '2026-03-01', '2026-03-31', 'outstanding', 314.99, 314.99,
     286.36, 28.63, 'monthly', '2026-03-01', '2026-03-31',
     15, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW()),
    
    -- Last month - Paid
    (gen_random_uuid(), :'MASTER_ORG_ID', 'INV-TECH-202602', 'subscription', :'TECH_ORG_ID',
     '2026-02-01', '2026-02-28', 'paid', 314.99, 0,
     286.36, 28.63, 'monthly', '2026-02-01', '2026-02-28',
     15, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW()),

-- Global Solutions Invoices (3 months)
    -- Current month - Outstanding  
    (gen_random_uuid(), :'MASTER_ORG_ID', 'INV-GLOBAL-202603', 'subscription', :'GLOBAL_ORG_ID',
     '2026-03-01', '2026-03-31', 'outstanding', 209.99, 209.99,
     190.90, 19.09, 'monthly', '2026-03-01', '2026-03-31',
     10, :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW());

-- 4. Create Invoice Items
ECHO 'Creating Invoice Items...';

-- Get invoice IDs for items
INSERT INTO invoice_items (
    id, organization_id, invoice_id, item_name, qty, uom, rate, amount, sort_order, created_at, updated_at
)
SELECT 
    gen_random_uuid(),
    i.organization_id,
    i.id,
    CASE 
        WHEN i.party_id = :'ACME_ORG_ID' THEN 'Enterprise Plan Subscription'
        WHEN i.party_id = :'TECH_ORG_ID' THEN 'Pro Plan Subscription' 
        ELSE 'Basic Plan Subscription'
    END,
    1,
    'month',
    CASE 
        WHEN i.party_id = :'ACME_ORG_ID' THEN 299.99
        WHEN i.party_id = :'TECH_ORG_ID' THEN 149.99
        ELSE 99.99
    END,
    CASE 
        WHEN i.party_id = :'ACME_ORG_ID' THEN 299.99
        WHEN i.party_id = :'TECH_ORG_ID' THEN 149.99 
        ELSE 99.99
    END,
    1,
    NOW(),
    NOW()
FROM invoices i WHERE i.organization_id = :'MASTER_ORG_ID' AND i.invoice_type = 'subscription';

-- Add seat charges
INSERT INTO invoice_items (
    id, organization_id, invoice_id, item_name, qty, uom, rate, amount, sort_order, created_at, updated_at
)
SELECT 
    gen_random_uuid(),
    i.organization_id, 
    i.id,
    'Additional User Seats',
    i.seat_count,
    'seats',
    CASE 
        WHEN i.party_id = :'ACME_ORG_ID' THEN 8.00  -- $8 per seat for enterprise
        WHEN i.party_id = :'TECH_ORG_ID' THEN 9.00  -- $9 per seat for pro
        ELSE 10.00                                   -- $10 per seat for basic
    END,
    CASE 
        WHEN i.party_id = :'ACME_ORG_ID' THEN i.seat_count * 8.00
        WHEN i.party_id = :'TECH_ORG_ID' THEN i.seat_count * 9.00
        ELSE i.seat_count * 10.00
    END,
    2,
    NOW(),
    NOW()
FROM invoices i WHERE i.organization_id = :'MASTER_ORG_ID' AND i.invoice_type = 'subscription';

-- 5. Create Payment Reminder Configurations
ECHO 'Creating Payment Reminder Configurations...';
INSERT INTO reminder_configs (
    id, organization_id, reminder_type, is_enabled, grace_period_days,
    first_reminder_days, second_reminder_days, final_notice_days, 
    auto_deactivate_days, reminder_frequency_days, max_reminders_per_stage,
    auto_deactivate_enabled, send_copy_to_admin, created_at, updated_at, created_by
) VALUES
    (gen_random_uuid(), :'ACME_ORG_ID', 'auto', true, 15, 30, 60, 90, 120, 7, 3, true, true, NOW(), NOW(), :'ADMIN_USER_ID'),
    (gen_random_uuid(), :'TECH_ORG_ID', 'auto', true, 10, 30, 60, 90, 120, 5, 3, true, true, NOW(), NOW(), :'ADMIN_USER_ID'),
    (gen_random_uuid(), :'GLOBAL_ORG_ID', 'manual', true, 30, 45, 75, 105, 135, 10, 2, false, true, NOW(), NOW(), :'ADMIN_USER_ID')
ON CONFLICT (organization_id) DO UPDATE SET
    updated_at = EXCLUDED.updated_at;

-- 6. Create Sample Payment Entries with Allocations
ECHO 'Creating Payment Entries and Allocations...';

-- Payment for Acme Corp Feb invoice (partial payment)
WITH acme_feb_invoice AS (
    SELECT id FROM invoices WHERE organization_id = :'MASTER_ORG_ID' AND invoice_no = 'INV-ACME-202602'
),
acme_payment AS (
    INSERT INTO payment_entries (
        id, organization_id, payment_type, party_id, amount, currency_code,
        payment_date, payment_mode, status, reference_no, source,
        created_by, updated_by, created_at, updated_at
    ) VALUES (
        gen_random_uuid(), :'MASTER_ORG_ID', 'Customer_Payment', :'ACME_ORG_ID', 385.00,  
        'USD', '2026-02-25', 'Bank_Transfer', 'Confirmed', 'PAY-ACME-20260225',
        'Manual', :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW()
    ) RETURNING id
)
INSERT INTO payment_references (
    id, organization_id, payment_id, invoice_id, allocated_amount, 
    created_by, created_at
)
SELECT 
    gen_random_uuid(), :'MASTER_ORG_ID', ap.id, afi.id, 385.00,
    :'ADMIN_USER_ID', NOW()
FROM acme_payment ap, acme_feb_invoice afi;

-- Payment for TechStart Feb invoice (full payment)  
WITH tech_feb_invoice AS (
    SELECT id FROM invoices WHERE organization_id = :'MASTER_ORG_ID' AND invoice_no = 'INV-TECH-202602'
),
tech_payment AS (
    INSERT INTO payment_entries (
        id, organization_id, payment_type, party_id, amount, currency_code,
        payment_date, payment_mode, status, reference_no, source,
        created_by, updated_by, created_at, updated_at
    ) VALUES (
        gen_random_uuid(), :'MASTER_ORG_ID', 'Customer_Payment', :'TECH_ORG_ID', 314.99,
        'USD', '2026-02-28', 'Bank_Transfer', 'Confirmed', 'PAY-TECH-20260228',
        'Manual', :'ADMIN_USER_ID', :'ADMIN_USER_ID', NOW(), NOW() 
    ) RETURNING id
)
INSERT INTO payment_references (
    id, organization_id, payment_id, invoice_id, allocated_amount,
    created_by, created_at  
)
SELECT
    gen_random_uuid(), :'MASTER_ORG_ID', tp.id, tfi.id, 314.99,
    :'ADMIN_USER_ID', NOW()
FROM tech_payment tp, tech_feb_invoice tfi;

-- 7. Create Sample Reminder Logs (simulate sent reminders for overdue invoices)
ECHO 'Creating Sample Reminder Logs...';
INSERT INTO reminder_logs (
    id, organization_id, invoice_id, reminder_stage, reminder_type, status,
    recipient_email, subject, sent_at, days_overdue, triggered_by,
    stage_attempt_number, created_at, updated_at  
)
SELECT
    gen_random_uuid(),
    CASE 
        WHEN i.party_id = :'ACME_ORG_ID' THEN :'ACME_ORG_ID'
        WHEN i.party_id = :'TECH_ORG_ID' THEN :'TECH_ORG_ID' 
        ELSE :'GLOBAL_ORG_ID'
    END,
    i.id,
    'first_reminder',
    'auto',
    'sent',
    CASE
        WHEN i.party_id = :'ACME_ORG_ID' THEN 'billing@acmecorp.com'
        WHEN i.party_id = :'TECH_ORG_ID' THEN 'finance@techstart.com'
        ELSE 'billing@globalsolutions.com'  
    END,
    'Payment Reminder: Outstanding Invoice ' || i.invoice_no,
    NOW() - INTERVAL '7 days',
    EXTRACT(DAYS FROM (NOW() - i.due_date))::int,
    'automated',
    1,
    NOW(),
    NOW()
FROM invoices i 
WHERE i.organization_id = :'MASTER_ORG_ID' 
  AND i.status = 'outstanding'
  AND i.due_date < NOW();

-- 8. Display Summary
ECHO '';
ECHO '✅ B2B TEST DATA SEEDING COMPLETED!';
ECHO '';
ECHO 'SUMMARY:';
ECHO '--------';

SELECT 
    'Organizations' as type,
    COUNT(*) as count
FROM (
    SELECT :'MASTER_ORG_ID' as id
    UNION SELECT :'ACME_ORG_ID'
    UNION SELECT :'TECH_ORG_ID' 
    UNION SELECT :'GLOBAL_ORG_ID'
) orgs;

SELECT 'Invoices' as type, COUNT(*) as count FROM invoices WHERE organization_id = :'MASTER_ORG_ID';
SELECT 'Invoice Items' as type, COUNT(*) as count FROM invoice_items WHERE organization_id = :'MASTER_ORG_ID';
SELECT 'Payment Entries' as type, COUNT(*) as count FROM payment_entries WHERE organization_id = :'MASTER_ORG_ID';
SELECT 'Payment References' as type, COUNT(*) as count FROM payment_references WHERE organization_id = :'MASTER_ORG_ID';
SELECT 'Reminder Configs' as type, COUNT(*) as count FROM reminder_configs WHERE organization_id IN (:'ACME_ORG_ID', :'TECH_ORG_ID', :'GLOBAL_ORG_ID');
SELECT 'Reminder Logs' as type, COUNT(*) as count FROM reminder_logs WHERE organization_id IN (:'ACME_ORG_ID', :'TECH_ORG_ID', :'GLOBAL_ORG_ID');

ECHO '';
ECHO 'TEST SCENARIOS READY:';
ECHO '1. B2B Billing Dashboard - Master org invoices only';  
ECHO '2. Outstanding invoice filtering and management';
ECHO '3. Payment reminder system with automated configs';
ECHO '4. Payment processing and allocation testing';
ECHO '5. Invoice aging and collection analytics';
ECHO '';
ECHO 'Access admin portal: http://localhost:3000/admin';
ECHO 'Use system admin credentials to test B2B filtering';
ECHO '';