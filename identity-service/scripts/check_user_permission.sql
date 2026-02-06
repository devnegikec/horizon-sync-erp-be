-- Check if user has *.* permission in a specific organization
-- Usage: Replace the UUIDs below with actual user_id and org_id

-- Set variables (PostgreSQL doesn't support variables in plain SQL, so replace manually)
-- user_id: 8d509f22-5fe5-4765-9496-3a236cae2af1
-- org_id: bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150

-- Step 1: Check current status
SELECT 
    u.id as user_id,
    u.email,
    o.id as org_id,
    o.name as org_name,
    r.id as role_id,
    r.name as role_name,
    r.code as role_code,
    p.code as permission_code,
    p.name as permission_name
FROM users u
JOIN user_organization_roles uor ON u.id = uor.user_id
JOIN organizations o ON uor.organization_id = o.id
JOIN roles r ON uor.role_id = r.id
LEFT JOIN role_permissions rp ON r.id = rp.role_id
LEFT JOIN permissions p ON rp.permission_id = p.id AND p.code = '*.*'
WHERE u.id = '8d509f22-5fe5-4765-9496-3a236cae2af1'::uuid
  AND o.id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'::uuid
  AND uor.is_active = true;

-- Step 2: Check if *.* permission exists
SELECT id, code, name 
FROM permissions 
WHERE code = '*.*';

-- Step 3: Get all permissions for this user in this org
SELECT DISTINCT p.code, p.name
FROM permissions p
JOIN role_permissions rp ON p.id = rp.permission_id
JOIN roles r ON rp.role_id = r.id
JOIN user_organization_roles uor ON r.id = uor.role_id
WHERE uor.user_id = '8d509f22-5fe5-4765-9496-3a236cae2af1'::uuid
  AND uor.organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'::uuid
  AND uor.is_active = true
  AND p.is_active = true
ORDER BY p.code;

-- Step 4: If *.* permission doesn't exist, create it
-- (Run this only if Step 2 returns no rows)
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

-- Step 5: Assign *.* permission to user's role(s) in this org
-- This will assign *.* to ALL roles the user has in this org
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

-- Step 6: Verify the assignment
SELECT 
    u.email,
    o.name as org_name,
    r.name as role_name,
    p.code as permission_code
FROM users u
JOIN user_organization_roles uor ON u.id = uor.user_id
JOIN organizations o ON uor.organization_id = o.id
JOIN roles r ON uor.role_id = r.id
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
WHERE u.id = '8d509f22-5fe5-4765-9496-3a236cae2af1'::uuid
  AND o.id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'::uuid
  AND uor.is_active = true
  AND p.code = '*.*';
