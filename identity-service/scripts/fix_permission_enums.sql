-- Fix permission rows with invalid enum values
-- PostgreSQL validates enum values even when reading, so we need to temporarily
-- add the invalid values to the enum types, update the rows, then remove them.

-- Step 1: Temporarily add invalid values to the enum types
-- This allows PostgreSQL to read/write rows with these values

-- Add 'org' to resourcetype enum (if not already present)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'org' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'resourcetype')
    ) THEN
        ALTER TYPE resourcetype ADD VALUE 'org';
    END IF;
END $$;

-- Add invalid action values to actiontype enum (if not already present)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = '*.*' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'actiontype')
    ) THEN
        ALTER TYPE actiontype ADD VALUE '*.*';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = '.*' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'actiontype')
    ) THEN
        ALTER TYPE actiontype ADD VALUE '.*';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'owner' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'actiontype')
    ) THEN
        ALTER TYPE actiontype ADD VALUE 'owner';
    END IF;
END $$;

-- Step 2: Now we can update the rows
-- Fix resource: 'org' -> 'organization'
UPDATE permissions 
SET resource = 'organization'::resourcetype
WHERE resource = 'org'::resourcetype;

-- Fix action: '*.*', '.*', 'owner' -> 'manage'
UPDATE permissions 
SET action = 'manage'::actiontype
WHERE action IN ('*.*'::actiontype, '.*'::actiontype, 'owner'::actiontype);

-- Step 3: Remove the temporary enum values (PostgreSQL doesn't support removing enum values directly)
-- Instead, we'll verify that all rows are fixed, then document that these enum values exist but shouldn't be used
-- Note: PostgreSQL doesn't allow removing enum values once added, but they won't cause issues if unused

-- Verify the fixes
SELECT id, code, resource, action 
FROM permissions 
WHERE resource = 'org'::resourcetype 
   OR action IN ('*.*'::actiontype, '.*'::actiontype, 'owner'::actiontype);

-- If the above query returns 0 rows, all invalid values have been fixed.
-- The temporary enum values ('org', '*.*', '.*', 'owner') will remain in the enum types
-- but won't be used since all rows have been updated to valid values.
