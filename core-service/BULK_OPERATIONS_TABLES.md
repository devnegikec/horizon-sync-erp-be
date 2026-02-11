# Bulk Import/Export Database Tables

## Overview
Two tables to support bulk item import and export operations in the core-service.

---

## Table: `bulk_import_jobs`

### Purpose
Tracks bulk item import jobs with status, statistics, and error details.

### Structure

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NO | gen_random_uuid() | Primary key |
| `organization_id` | UUID | NO | - | Organization that owns this job |
| `created_by_id` | UUID | NO | - | User who created the job |
| `file_name` | VARCHAR(255) | NO | - | Name of uploaded file |
| `file_path` | VARCHAR(255) | YES | NULL | Path to uploaded file |
| `mime_type` | VARCHAR(100) | NO | - | File MIME type |
| `status` | VARCHAR(20) | NO | 'PENDING' | Job status (PENDING, PROCESSING, COMPLETED, FAILED) |
| `total_rows` | INTEGER | NO | 0 | Total rows processed |
| `successful_rows` | INTEGER | NO | 0 | Successfully imported rows |
| `failed_rows` | INTEGER | NO | 0 | Failed rows |
| `error_details` | JSONB | YES | NULL | Row-wise error details |
| `summary` | TEXT | YES | NULL | Job summary message |
| `created_at` | TIMESTAMPTZ | NO | NOW() | Job creation timestamp |
| `updated_at` | TIMESTAMPTZ | NO | NOW() | Last update timestamp |
| `completed_at` | TIMESTAMPTZ | YES | NULL | Job completion timestamp |

### Indexes
- `idx_bulk_import_jobs_organization_id` on `organization_id`
- `idx_bulk_import_jobs_status` on `status`
- `idx_bulk_import_jobs_created_at` on `created_at DESC`

### Constraints
- `chk_bulk_import_status`: status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')

### Error Details JSON Structure
```json
{
  "errors": [
    {
      "row_number": 5,
      "errors": ["Missing required field 'item_name'"],
      "data": {"item_code": "ITEM001", "item_name": null}
    }
  ]
}
```

---

## Table: `bulk_export_jobs`

### Purpose
Tracks bulk item export jobs with filters and file generation.

### Structure

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NO | gen_random_uuid() | Primary key |
| `organization_id` | UUID | NO | - | Organization that owns this job |
| `created_by_id` | UUID | NO | - | User who created the job |
| `file_name` | VARCHAR(255) | NO | - | Name of export file |
| `file_path` | VARCHAR(255) | YES | NULL | Path to generated file |
| `file_format` | VARCHAR(20) | NO | - | Export format (csv, xlsx, json) |
| `status` | VARCHAR(20) | NO | 'PENDING' | Job status |
| `total_rows` | VARCHAR(20) | NO | '0' | Number of rows exported |
| `filters` | JSONB | YES | NULL | Export filters applied |
| `selected_columns` | JSONB | YES | NULL | Columns included in export |
| `error_message` | TEXT | YES | NULL | Error message if failed |
| `created_at` | TIMESTAMPTZ | NO | NOW() | Job creation timestamp |
| `updated_at` | TIMESTAMPTZ | NO | NOW() | Last update timestamp |
| `completed_at` | TIMESTAMPTZ | YES | NULL | Job completion timestamp |
| `expires_at` | TIMESTAMPTZ | YES | NULL | File expiration timestamp |

### Indexes
- `idx_bulk_export_jobs_organization_id` on `organization_id`
- `idx_bulk_export_jobs_status` on `status`
- `idx_bulk_export_jobs_created_at` on `created_at DESC`
- `idx_bulk_export_jobs_expires_at` on `expires_at`

### Constraints
- `chk_bulk_export_status`: status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')
- `chk_bulk_export_format`: file_format IN ('csv', 'xlsx', 'json')

### Filters JSON Structure
```json
{
  "item_type": "Stock",
  "status": "Active",
  "item_group_id": "123e4567-e89b-12d3-a456-426614174000",
  "search": "widget"
}
```

### Selected Columns JSON Structure
```json
["id", "item_code", "item_name", "description", "status", "standard_rate"]
```

---

## Installation

### Option 1: Using the SQL Script
```bash
# Execute the SQL script directly
psql -U horizon_user -d core_db -f core-service/scripts/create_bulk_import_export_tables.sql

# Or using Docker
cat core-service/scripts/create_bulk_import_export_tables.sql | docker exec -i horizon_postgres psql -U horizon_user -d core_db
```

### Option 2: Using Alembic Migration
```bash
# Run from core-service directory
cd core-service
python -m alembic upgrade head
```

---

## API Endpoints

### Bulk Import
- `POST /api/v1/bulk-import/upload` - Upload file for import
- `GET /api/v1/bulk-import/{job_id}/status` - Get job status
- `GET /api/v1/bulk-import/{job_id}/errors` - Get error details
- `GET /api/v1/bulk-import` - List import jobs
- `GET /api/v1/bulk-import/template/csv` - Download CSV template
- `GET /api/v1/bulk-import/template/xlsx` - Download XLSX template

### Bulk Export
- `POST /api/v1/bulk-export` - Create export job
- `GET /api/v1/bulk-export/{job_id}/status` - Get job status
- `GET /api/v1/bulk-export/{job_id}/download` - Download exported file
- `GET /api/v1/bulk-export` - List export jobs
- `POST /api/v1/bulk-export/quick` - Quick export without job tracking

---

## Triggers

### Auto-update `updated_at`
Both tables have triggers that automatically update the `updated_at` column on any UPDATE operation.

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## Verification Queries

### Check table creation
```sql
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_name IN ('bulk_import_jobs', 'bulk_export_jobs')
ORDER BY table_name;
```

### View recent import jobs
```sql
SELECT 
    id,
    file_name,
    status,
    total_rows,
    successful_rows,
    failed_rows,
    created_at,
    completed_at
FROM bulk_import_jobs
WHERE organization_id = 'YOUR_ORG_ID'
ORDER BY created_at DESC
LIMIT 10;
```

### View recent export jobs
```sql
SELECT 
    id,
    file_name,
    file_format,
    status,
    total_rows,
    created_at,
    expires_at
FROM bulk_export_jobs
WHERE organization_id = 'YOUR_ORG_ID'
ORDER BY created_at DESC
LIMIT 10;
```

### Check for failed imports with errors
```sql
SELECT 
    id,
    file_name,
    failed_rows,
    error_details->'errors' as error_list,
    created_at
FROM bulk_import_jobs
WHERE status = 'FAILED' OR failed_rows > 0
ORDER BY created_at DESC;
```

---

## Maintenance

### Cleanup expired exports
```sql
-- Delete export jobs older than 30 days
DELETE FROM bulk_export_jobs
WHERE expires_at < NOW() - INTERVAL '30 days';
```

### Archive old import jobs
```sql
-- Archive import jobs older than 90 days
-- (Move to archive table or delete based on your retention policy)
DELETE FROM bulk_import_jobs
WHERE created_at < NOW() - INTERVAL '90 days'
AND status IN ('COMPLETED', 'FAILED');
```
