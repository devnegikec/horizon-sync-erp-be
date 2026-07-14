-- =========================================
-- ACCOUNTS TABLES CLEANUP SCRIPT
-- =========================================
-- This script safely cleans up accounts and default_accounts tables
-- Run this script carefully in your database management tool
--
-- IMPORTANT: Always backup your data before running this script
--
-- Usage:
--   1. Connect to your database 
--   2. Run the inspection queries first
--   3. Optionally create backups
--   4. Run the cleanup queries
-- =========================================

-- 1. INSPECT CURRENT STATE
-- =========================================
-- Check if tables exist and get current row counts

SELECT 
    'accounts' as table_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'accounts'
    ) THEN 'EXISTS' ELSE 'MISSING' END as status,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'accounts'
    ) THEN (SELECT COUNT(*) FROM accounts) ELSE 0 END as row_count

UNION ALL

SELECT 
    'default_accounts' as table_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'default_accounts'
    ) THEN 'EXISTS' ELSE 'MISSING' END as status,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'default_accounts'
    ) THEN (SELECT COUNT(*) FROM default_accounts) ELSE 0 END as row_count;


-- 2. SAMPLE DATA PREVIEW (Optional)
-- =========================================
-- Preview some sample data to understand what will be deleted

-- Sample accounts data (first 5 rows)
SELECT 'accounts' as table_name, account_code, account_name, account_type
FROM accounts 
LIMIT 5;

-- Sample default_accounts data (first 5 rows) 
SELECT 'default_accounts' as table_name, organization_id, transaction_type, scenario
FROM default_accounts
LIMIT 5;


-- 3. DATA BACKUP (Recommended)
-- =========================================
-- Create backup tables before cleanup (uncomment if needed)

/*
-- Backup accounts table
CREATE TABLE accounts_backup_20260313 AS 
SELECT * FROM accounts;

-- Backup default_accounts table  
CREATE TABLE default_accounts_backup_20260313 AS 
SELECT * FROM default_accounts;

-- Verify backups were created
SELECT COUNT(*) as accounts_backup_rows FROM accounts_backup_20260313;
SELECT COUNT(*) as default_accounts_backup_rows FROM default_accounts_backup_20260313;
*/


-- 4. CLEANUP QUERIES
-- =========================================
-- WARNING: These queries will permanently delete data
-- Only run after confirming backups are complete

-- Begin transaction for safety
BEGIN;

-- Clean default_accounts first (due to foreign key constraints)
TRUNCATE TABLE default_accounts CASCADE;

-- Clean accounts table
TRUNCATE TABLE accounts CASCADE;

-- Verify cleanup
SELECT 
    'accounts' as table_name,
    COUNT(*) as remaining_rows
FROM accounts

UNION ALL

SELECT 
    'default_accounts' as table_name, 
    COUNT(*) as remaining_rows
FROM default_accounts;

-- Commit the transaction (uncomment when ready)
-- COMMIT;

-- Or rollback if something looks wrong
-- ROLLBACK;


-- 5. CLEANUP VERIFICATION
-- =========================================
-- Run after cleanup to verify success

SELECT 
    table_name,
    table_rows as estimated_rows
FROM information_schema.tables 
WHERE table_name IN ('accounts', 'default_accounts')
  AND table_schema = current_schema();


-- 6. REMOVE BACKUP TABLES (Optional)
-- =========================================
-- Clean up backup tables after confirming cleanup success

/*
DROP TABLE IF EXISTS accounts_backup_20260313;
DROP TABLE IF EXISTS default_accounts_backup_20260313;
*/


-- =========================================
-- ALTERNATIVE: DELETE BY ORGANIZATION
-- =========================================
-- If you want to clean up data for specific organization(s) only

/*
-- Replace 'your-org-id-here' with actual organization UUID
-- DELETE FROM default_accounts WHERE organization_id = 'your-org-id-here';
-- DELETE FROM accounts WHERE organization_id = 'your-org-id-here';
*/


-- =========================================
-- RESET SEQUENCES (PostgreSQL)
-- =========================================
-- Reset auto-increment sequences if using SERIAL columns

/*
-- Reset accounts sequence (if using SERIAL id column)
ALTER SEQUENCE accounts_id_seq RESTART WITH 1;

-- Reset default_accounts sequence (if using SERIAL id column) 
ALTER SEQUENCE default_accounts_id_seq RESTART WITH 1;
*/