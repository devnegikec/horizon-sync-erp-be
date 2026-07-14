-- Fix Alembic Version Table
-- This script fixes the alembic_version table to point to the correct migration

-- Check current version
SELECT * FROM alembic_version;

-- Delete the incorrect version reference
DELETE FROM alembic_version WHERE version_num = '022_add_performance_indexes';

-- Set to the latest actual migration file
-- Option 1: If you want to start fresh from 021
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('021_create_missing_accounts');

-- Option 2: If you want to go back to 020 and re-run 021
-- DELETE FROM alembic_version;
-- INSERT INTO alembic_version (version_num) VALUES ('020_add_bank_account_id_payment');

-- Verify the fix
SELECT * FROM alembic_version;
