-- cleanup_duplicate_items.sql
-- Purpose: find and remove duplicate `items` rows that share the same
-- (organization_id, item_code) so the unique constraint migration can succeed.
-- IMPORTANT: Review results before running destructive steps. Run in a transaction
-- and take a full DB backup before applying to production.

-- Usage (example):
--   psql "$DATABASE_URL" -f core-service/db_scripts/cleanup_duplicate_items.sql

-- 1) Preview duplicate groups (do NOT modify data):
SELECT organization_id, item_code, count(*) AS cnt
FROM items
GROUP BY organization_id, item_code
HAVING count(*) > 1
ORDER BY cnt DESC;

-- 2) Inspect rows for a single duplicate group (replace the ids below):
-- SELECT * FROM items WHERE organization_id='186fe4b9-a509-42e9-9d99-b0b8660da1ae' AND item_code='ITM-2026-00011' ORDER BY created_at, id;

-- 3) BACKUP duplicate rows (non-destructive):
-- This creates or appends to a backup table that stores rows that would be deleted.
BEGIN;
CREATE TABLE IF NOT EXISTS items_duplicates_backup (LIKE items INCLUDING ALL);
INSERT INTO items_duplicates_backup
SELECT * FROM items
WHERE id IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY organization_id, item_code ORDER BY created_at ASC, id ASC) rn
    FROM items
  ) t WHERE t.rn > 1
);
-- Verify how many rows were backed up:
SELECT count(*) AS backed_up FROM items_duplicates_backup;
COMMIT;

-- 4) OPTIONAL: Dry-run delete list (shows ids that WOULD be deleted):
SELECT id, organization_id, item_code, created_at FROM (
  SELECT id, organization_id, item_code, created_at,
         ROW_NUMBER() OVER (PARTITION BY organization_id, item_code ORDER BY created_at ASC, id ASC) rn
  FROM items
) t WHERE t.rn > 1 ORDER BY organization_id, item_code;

-- 5) Delete duplicates keeping the earliest created_at row per (organization_id, item_code).
-- WARNING: run only after you have verified the backup above and are comfortable to delete.
BEGIN;
WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY organization_id, item_code ORDER BY created_at ASC, id ASC) rn
  FROM items
)
DELETE FROM items WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
-- Re-check duplicates (should return zero rows):
SELECT organization_id, item_code, count(*) AS cnt
FROM items
GROUP BY organization_id, item_code
HAVING count(*) > 1;
COMMIT;

-- 6) (Optional) If everything looks good, re-run the migration to add the unique constraint.
-- e.g. run on the application host:
--   alembic upgrade head

-- NOTES / CAVEATS:
-- - This script only deletes duplicate rows in `items`. If other tables reference the deleted
--   item ids (foreign keys), you MUST consider migrating or re-linking those references first.
-- - For a safer approach, instead of deleting rows, you may want to merge related child records
--   from duplicate item rows onto the kept row. That requires application-specific logic.
-- - Always test the script on a staging copy of the database first.
