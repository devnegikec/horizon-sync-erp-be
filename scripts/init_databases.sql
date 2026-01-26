-- ===========================================
-- Horizon Sync Backend - Database Initialization
-- Creates separate databases for each service
-- ===========================================

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
-- Grant privileges to horizon_user
-- ===========================================
GRANT ALL PRIVILEGES ON DATABASE identity_db TO horizon_user;
GRANT ALL PRIVILEGES ON DATABASE core_db TO horizon_user;

-- ===========================================
-- Initialize Identity Database
-- ===========================================
\connect identity_db;

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
    'permission'
);

CREATE TYPE actiontype AS ENUM (
    'create',
    'read',
    'update',
    'delete',
    'manage',
    'execute'
);

-- ===========================================
-- Initialize Core Database
-- ===========================================
\connect core_db;

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
