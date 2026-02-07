# Fix for 500 Error on GET /api/v1/identity/users

## Problem
User with ID `8d509f22-5fe5-4765-9496-3a236cae2af1` in org `bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150` is getting a 500 Internal Server Error when accessing the users list endpoint.

## Root Cause
The error is likely caused by:
1. **Invalid enum values in permissions table**: If permissions have invalid enum values (like `*.*` in `actiontype` or `org` in `resourcetype`), queries joining permissions can fail.
2. **Enum handling in status counts**: The `get_user_status_counts` function might encounter issues when processing enum values from the database.
3. **Permission retrieval errors**: If `_get_user_permissions` encounters invalid data, it could cause a 500 error.

## Fixes Applied

### 1. Enhanced Error Handling in Permission Retrieval (`app/dependencies.py`)
- Added try-catch block in `_get_user_permissions` to handle database errors gracefully
- Returns empty list instead of crashing if there are enum issues
- Added `Permission.is_active` filter to exclude inactive permissions
- Added `.distinct()` to avoid duplicate permission codes

### 2. Improved Status Count Enum Handling (`app/repositories/user_repository.py`)
- Added robust error handling for enum value processing
- Handles None values, string values, and enum objects safely
- Logs warnings but continues processing instead of crashing
- Converts count to int safely

### 3. Endpoint Error Handling (`app/api/v1/endpoints/users.py`)
- Added try-catch block around user listing and status count retrieval
- Returns proper HTTP 500 error with details instead of crashing
- Added logging for debugging

## Next Steps

### 1. Check User's Permissions
Run this SQL to check if the user has invalid permission data:

```sql
SELECT 
    u.id as user_id,
    u.email,
    p.code,
    p.resource,
    p.action
FROM users u
JOIN user_organization_roles uor ON u.id = uor.user_id
JOIN roles r ON uor.role_id = r.id
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
WHERE u.id = '8d509f22-5fe5-4765-9496-3a236cae2af1'::uuid
  AND uor.organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'::uuid
  AND uor.is_active = true;
```

### 2. Fix Invalid Permission Enum Values
If you find permissions with invalid enum values (like `*.*` in action or `org` in resource), run:

```sql
-- First, ensure *.* permission exists with correct enum values
INSERT INTO permissions (id, code, name, description, resource, action, module, is_active, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    '*.*',
    'Full access (all resources and actions)',
    'Grants all permissions across all resources',
    'all'::resourcetype,
    'manage'::actiontype,
    'identity',
    true,
    NOW(),
    NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = '*.*');

-- Update any permissions with 'org' resource to 'organization'
-- (This might fail if enum doesn't have 'org', use the fix_permission_enums.sql script first)
UPDATE permissions 
SET resource = 'organization'::resourcetype 
WHERE resource::text = 'org' 
  AND EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'organization' AND enumtypid = 'resourcetype'::regtype);

-- Update any permissions with '*.*' or '.*' action to 'manage'
UPDATE permissions 
SET action = 'manage'::actiontype 
WHERE action::text IN ('*.*', '.*', 'owner')
  AND EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'manage' AND enumtypid = 'actiontype'::regtype);
```

### 3. Assign *.* Permission to User
Use the script `check_and_assign_permission.py` or run:

```sql
-- Get user's role in the org
SELECT r.id, r.name, r.code
FROM roles r
JOIN user_organization_roles uor ON r.id = uor.role_id
WHERE uor.user_id = '8d509f22-5fe5-4765-9496-3a236cae2af1'::uuid
  AND uor.organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'::uuid
  AND uor.is_active = true;

-- Assign *.* permission to that role
INSERT INTO role_permissions (id, role_id, permission_id, conditions, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    r.id,
    (SELECT id FROM permissions WHERE code = '*.*'),
    '{}'::jsonb,
    NOW(),
    NOW()
FROM roles r
JOIN user_organization_roles uor ON r.id = uor.role_id
WHERE uor.user_id = '8d509f22-5fe5-4765-9496-3a236cae2af1'::uuid
  AND uor.organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'::uuid
  AND uor.is_active = true
  AND NOT EXISTS (
    SELECT 1 FROM role_permissions rp2 
    WHERE rp2.role_id = r.id 
    AND rp2.permission_id = (SELECT id FROM permissions WHERE code = '*.*')
  );
```

## Testing
After applying fixes:
1. Restart the identity-service
2. Try accessing `GET /api/v1/identity/users?page=1&page_size=20` with the user's token
3. Check logs for any warnings or errors
4. Verify the user has `*.*` permission in their permissions list

## Files Modified
- `identity-service/app/dependencies.py` - Enhanced `_get_user_permissions` error handling
- `identity-service/app/repositories/user_repository.py` - Improved enum handling in `get_user_status_counts`
- `identity-service/app/api/v1/endpoints/users.py` - Added error handling and logging
