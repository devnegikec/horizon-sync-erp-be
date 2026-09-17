-- ============================================================
-- Horizon Sync Backend - Local 'railway' database bootstrap
-- ============================================================
-- Runs as the postgres superuser during container initialization,
-- against the default database (POSTGRES_DB=railway).
--
-- This mirrors the Railway deployment: a single shared 'railway'
-- database. All tables/types are created by each service's Alembic
-- migrations on startup, so only the UUID extension is needed here.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
