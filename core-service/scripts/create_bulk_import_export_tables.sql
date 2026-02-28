-- =====================================================
-- Bulk Import/Export Tables Creation Script
-- =====================================================
-- Created: 2026-02-03
-- Purpose: Add tables for bulk item import and export functionality
-- Database: core_db
-- =====================================================

-- Table: bulk_import_jobs
-- Purpose: Track bulk item import jobs with status, statistics, and errors
CREATE TABLE IF NOT EXISTS bulk_import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    created_by_id UUID NOT NULL,

    -- File Information
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255),
    mime_type VARCHAR(100) NOT NULL,

    -- Job Status
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    -- Statistics
    total_rows INTEGER NOT NULL DEFAULT 0,
    successful_rows INTEGER NOT NULL DEFAULT 0,
    failed_rows INTEGER NOT NULL DEFAULT 0,

    -- Error Details (JSON format for row-wise errors)
    error_details JSONB,

    -- Summary information
    summary TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Indexes
    CONSTRAINT chk_bulk_import_status CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'))
);

-- Create indexes for bulk_import_jobs
CREATE INDEX IF NOT EXISTS idx_bulk_import_jobs_organization_id ON bulk_import_jobs(organization_id);
CREATE INDEX IF NOT EXISTS idx_bulk_import_jobs_status ON bulk_import_jobs(status);
CREATE INDEX IF NOT EXISTS idx_bulk_import_jobs_created_at ON bulk_import_jobs(created_at DESC);

-- =====================================================

-- Table: bulk_export_jobs
-- Purpose: Track bulk item export jobs with filters and file generation
CREATE TABLE IF NOT EXISTS bulk_export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    created_by_id UUID NOT NULL,

    -- File Information
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255),
    file_format VARCHAR(20) NOT NULL,

    -- Job Status
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    -- Statistics
    total_rows VARCHAR(20) NOT NULL DEFAULT '0',

    -- Filter Information (JSON format)
    filters JSONB,

    -- Column Selection (JSON array)
    selected_columns JSONB,

    -- Error Details
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT chk_bulk_export_status CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    CONSTRAINT chk_bulk_export_format CHECK (file_format IN ('csv', 'xlsx', 'json', 'pdf'))
);

-- Create indexes for bulk_export_jobs
CREATE INDEX IF NOT EXISTS idx_bulk_export_jobs_organization_id ON bulk_export_jobs(organization_id);
CREATE INDEX IF NOT EXISTS idx_bulk_export_jobs_status ON bulk_export_jobs(status);
CREATE INDEX IF NOT EXISTS idx_bulk_export_jobs_created_at ON bulk_export_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bulk_export_jobs_expires_at ON bulk_export_jobs(expires_at);

-- =====================================================
-- Trigger: Auto-update updated_at timestamp
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for bulk_import_jobs
DROP TRIGGER IF EXISTS update_bulk_import_jobs_updated_at ON bulk_import_jobs;
CREATE TRIGGER update_bulk_import_jobs_updated_at
    BEFORE UPDATE ON bulk_import_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for bulk_export_jobs
DROP TRIGGER IF EXISTS update_bulk_export_jobs_updated_at ON bulk_export_jobs;
CREATE TRIGGER update_bulk_export_jobs_updated_at
    BEFORE UPDATE ON bulk_export_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Comments on tables and columns
-- =====================================================

COMMENT ON TABLE bulk_import_jobs IS 'Tracks bulk item import jobs with status, errors, and statistics';
COMMENT ON COLUMN bulk_import_jobs.organization_id IS 'Organization that owns this import job';
COMMENT ON COLUMN bulk_import_jobs.created_by_id IS 'User who created the import job';
COMMENT ON COLUMN bulk_import_jobs.status IS 'Current status: PENDING, PROCESSING, COMPLETED, FAILED';
COMMENT ON COLUMN bulk_import_jobs.error_details IS 'JSON object containing row-wise error details';

COMMENT ON TABLE bulk_export_jobs IS 'Tracks bulk item export jobs with filters and file generation';
COMMENT ON COLUMN bulk_export_jobs.organization_id IS 'Organization that owns this export job';
COMMENT ON COLUMN bulk_export_jobs.created_by_id IS 'User who created the export job';
COMMENT ON COLUMN bulk_export_jobs.file_format IS 'Export format: csv, xlsx, or json';
COMMENT ON COLUMN bulk_export_jobs.filters IS 'JSON object containing export filters';
COMMENT ON COLUMN bulk_export_jobs.selected_columns IS 'JSON array of column names to include in export';
COMMENT ON COLUMN bulk_export_jobs.expires_at IS 'When the exported file expires (default 24 hours)';

-- =====================================================
-- Grant permissions (adjust as needed for your setup)
-- =====================================================

-- GRANT SELECT, INSERT, UPDATE, DELETE ON bulk_import_jobs TO horizon_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON bulk_export_jobs TO horizon_user;

-- =====================================================
-- Verification queries
-- =====================================================

-- Verify tables were created
SELECT
    table_name,
    table_type
FROM information_schema.tables
WHERE table_name IN ('bulk_import_jobs', 'bulk_export_jobs')
ORDER BY table_name;

-- Verify columns
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name IN ('bulk_import_jobs', 'bulk_export_jobs')
ORDER BY table_name, ordinal_position;

-- =====================================================
-- Sample usage queries
-- =====================================================

-- Query to check import job status
-- SELECT
--     id,
--     file_name,
--     status,
--     total_rows,
--     successful_rows,
--     failed_rows,
--     created_at,
--     completed_at
-- FROM bulk_import_jobs
-- WHERE organization_id = 'YOUR_ORG_ID'
-- ORDER BY created_at DESC;

-- Query to check export job status
-- SELECT
--     id,
--     file_name,
--     file_format,
--     status,
--     total_rows,
--     created_at,
--     expires_at
-- FROM bulk_export_jobs
-- WHERE organization_id = 'YOUR_ORG_ID'
-- ORDER BY created_at DESC;

-- =====================================================
-- END OF SCRIPT
-- =====================================================
