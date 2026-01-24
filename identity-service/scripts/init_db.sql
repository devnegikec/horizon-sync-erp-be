-- Database initialization script for Identity Service
-- Creates custom enum types and extensions

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom enum types
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
