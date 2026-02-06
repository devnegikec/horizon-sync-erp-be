-- Alternative fix: Use PL/pgSQL to bypass enum validation
-- This approach doesn't require altering enum types

-- Fix resource: 'org' -> 'organization'
DO $$
DECLARE
    row_record RECORD;
BEGIN
    -- Use a cursor to iterate over rows with invalid enum values
    -- We'll read the raw text value and update using the row's primary key
    FOR row_record IN 
        SELECT id, code
        FROM permissions
        WHERE (resource::text = 'org' OR action::text IN ('*.*', '.*', 'owner'))
    LOOP
        -- Update resource if it's 'org'
        IF EXISTS (
            SELECT 1 FROM permissions 
            WHERE id = row_record.id 
            AND resource::text = 'org'
        ) THEN
            UPDATE permissions 
            SET resource = 'organization'::resourcetype
            WHERE id = row_record.id;
        END IF;
        
        -- Update action if it's invalid
        IF EXISTS (
            SELECT 1 FROM permissions 
            WHERE id = row_record.id 
            AND action::text IN ('*.*', '.*', 'owner')
        ) THEN
            UPDATE permissions 
            SET action = 'manage'::actiontype
            WHERE id = row_record.id;
        END IF;
    END LOOP;
END $$;

-- Verify the fixes
SELECT id, code, resource::text as resource_text, action::text as action_text
FROM permissions 
WHERE resource::text = 'org' OR action::text IN ('*.*', '.*', 'owner');

-- If the above query returns 0 rows, all invalid values have been fixed.
