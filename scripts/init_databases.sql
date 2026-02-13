-- ===========================================
-- Horizon Sync Backend - Database Initialization
-- Creates separate databases for each service
-- ===========================================
-- This script runs as the postgres superuser during container initialization
-- It runs against the default database specified by POSTGRES_DB (usually 'postgres')

-- Ensure we're connected to the default database
\c postgres;

-- Enable UUID extension for the default database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- Create Identity Database
-- ===========================================
CREATE DATABASE identity_db;

-- ===========================================
-- Create Core Database
-- ===========================================
CREATE DATABASE core_db;

-- ===========================================
-- Create Search Database
-- ===========================================
CREATE DATABASE search_db;

-- ===========================================
-- Grant privileges to horizon_user
-- ===========================================
-- Note: horizon_user is created by POSTGRES_USER env var
GRANT ALL PRIVILEGES ON DATABASE identity_db TO horizon_user;
GRANT ALL PRIVILEGES ON DATABASE core_db TO horizon_user;
GRANT ALL PRIVILEGES ON DATABASE search_db TO horizon_user;

-- ===========================================
-- Initialize Identity Database
-- ===========================================
-- Connect to identity_db (must be explicit)
\c identity_db;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom enum types for Identity Service
CREATE TYPE usertype AS ENUM (
    'system_admin',
    'organization_admin',
    'user',
    'guest'
);

CREATE TYPE userstatus AS ENUM (
    'active',
    'inactive',
    'suspended',
    'pending'
);

CREATE TYPE organizationtype AS ENUM (
    'enterprise',
    'business',
    'startup',
    'individual'
);

CREATE TYPE organizationstatus AS ENUM (
    'active',
    'inactive',
    'suspended',
    'trial'
);

CREATE TYPE teamrole AS ENUM (
    'owner',
    'admin',
    'member',
    'viewer'
);

CREATE TYPE teamtype AS ENUM (
    'department',
    'project',
    'functional',
    'cross_functional'
);

CREATE TYPE resourcetype AS ENUM (
    'user',
    'organization',
    'team',
    'role',
    'permission',
    'invitation',
    'item',
    'item_group',
    'warehouse',
    'stock_entry',
    'batch',
    'serial',
    'report',
    'setting',
    'all'
);

CREATE TYPE actiontype AS ENUM (
    'create',
    'read',
    'update',
    'delete',
    'manage',
    'execute',
    'invite'
);

-- ===========================================
-- Initialize Core Database
-- ===========================================
-- Connect to core_db (must be explicit)
\c core_db;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom enum types for Core Service (Inventory)
CREATE TYPE itemtype AS ENUM (
    'stock',
    'non_stock',
    'service',
    'fixed_asset'
);

CREATE TYPE itemstatus AS ENUM (
    'active',
    'inactive',
    'discontinued'
);

CREATE TYPE valuationmethod AS ENUM (
    'fifo',
    'lifo',
    'moving_average',
    'standard'
);

CREATE TYPE documentstatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);

CREATE TYPE warehousetype AS ENUM (
    'warehouse',
    'store',
    'virtual',
    'transit'
);

CREATE TYPE stockentrytype AS ENUM (
    'material_receipt',
    'material_issue',
    'material_transfer',
    'manufacture',
    'repack',
    'send_to_subcontractor'
);

CREATE TYPE stockentrystatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);

CREATE TYPE movementtype AS ENUM (
    'in',
    'out',
    'transfer',
    'adjustment'
);

CREATE TYPE batchstatus AS ENUM (
    'active',
    'expired',
    'consumed'
);

CREATE TYPE inspectiontype AS ENUM (
    'incoming',
    'outgoing',
    'in_process'
);

CREATE TYPE inspectionstatus AS ENUM (
    'pending',
    'accepted',
    'rejected'
);

CREATE TYPE readingtype AS ENUM (
    'numeric',
    'text',
    'pass_fail'
);

-- ===========================================
-- Initialize Search Database
-- ===========================================
-- Connect to search_db (must be explicit)
\c search_db;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search
