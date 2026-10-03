-- ============================================================
-- Horizon Sync Backend — local database bootstrap
-- ============================================================
-- Runs once on a FRESH volume, against POSTGRES_DB (`postgres`).
-- Creates the two local databases (core + identity) and enables the UUID
-- extension in each. Tables are created by each service's Alembic migrations
-- (CI/CD), so nothing else is needed here.

-- Create both databases (idempotent).
SELECT 'CREATE DATABASE core_db'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'core_db') \gexec

SELECT 'CREATE DATABASE identity_db'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'identity_db') \gexec

-- Enable UUID generation in each database.
\connect core_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\connect identity_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
