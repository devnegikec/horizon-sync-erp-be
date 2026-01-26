-- 1. Wipe existing data to ensure a clean state
TRUNCATE TABLE user_organization_roles, role_permissions, roles, users, permissions, organizations CASCADE;

-- 2. Create Default Organization
INSERT INTO organizations (
    id, name, slug, display_name, description, organization_type, status, is_active, created_at, updated_at
) VALUES (
    gen_random_uuid(), 'Default Organization', 'default-org', 'Default Organization',
    'Default organization for the system', 'business', 'active', true, NOW(), NOW()
);

-- 3. Create Roles
INSERT INTO roles (id, organization_id, name, code, description, is_system, is_default, is_active, hierarchy_level, created_at, updated_at)
VALUES
(gen_random_uuid(), (SELECT id FROM organizations WHERE slug = 'default-org'), 'System Administrator', 'system_admin', 'Full system access', true, false, true, 100, NOW(), NOW()),
(gen_random_uuid(), (SELECT id FROM organizations WHERE slug = 'default-org'), 'Organization Administrator', 'org_admin', 'Org-level admin access', true, false, true, 50, NOW(), NOW()),
(gen_random_uuid(), (SELECT id FROM organizations WHERE slug = 'default-org'), 'User', 'user', 'Standard user access', true, true, true, 10, NOW(), NOW());

-- 4. Create Permissions
INSERT INTO permissions (id, code, name, resource, action, module, is_active, created_at, updated_at)
VALUES
(gen_random_uuid(), 'user.create', 'Create User', 'user', 'create', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'user.read',   'Read User',   'user', 'read',   'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'user.update', 'Update User', 'user', 'update', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'user.delete', 'Delete User', 'user', 'delete', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'user.manage', 'Manage Users', 'user', 'manage', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'org.create',  'Create Org',  'organization', 'create', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'org.read',    'Read Org',    'organization', 'read',   'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'org.update',  'Update Org',  'organization', 'update', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'org.delete',  'Delete Org',  'organization', 'delete', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'org.manage',  'Manage Orgs', 'organization', 'manage', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'role.create', 'Create Role', 'role', 'create', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'role.read',   'Read Role',   'role', 'read',   'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'role.update', 'Update Role', 'role', 'update', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'role.delete', 'Delete Role', 'role', 'delete', 'identity', true, NOW(), NOW()),
(gen_random_uuid(), 'role.manage', 'Manage Roles','role', 'manage', 'identity', true, NOW(), NOW());

-- 5. Assign Permissions to Roles
INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), (SELECT id FROM roles WHERE code = 'system_admin'), id FROM permissions;

-- 6. Create Test Users
INSERT INTO users (id, email, password_hash, first_name, last_name, display_name, user_type, status, email_verified, is_active, created_at, updated_at)
VALUES
(gen_random_uuid(), 'admin@example.com', '$2b$12$6B9P7G/R5T2Z/K1V5W8X9OqYlZ9.S6p0B3V2G1f5f5f5f5f5f5f5f', 'System', 'Administrator', 'System Administrator', 'system_admin', 'active', true, true, NOW(), NOW()),
(gen_random_uuid(), 'john.doe@example.com', '$2b$12$6B9P7G/R5T2Z/K1V5W8X9OqYlZ9.S6p0B3V2G1f5f5f5f5f5f5f5f', 'John', 'Doe', 'John Doe', 'user', 'active', true, true, NOW(), NOW());

-- 7. Link Users to Organizations and Roles (Added created_at/updated_at)
INSERT INTO user_organization_roles (id, user_id, organization_id, role_id, is_primary, is_active, status, joined_at, created_at, updated_at)
VALUES
(
    gen_random_uuid(),
    (SELECT id FROM users WHERE email = 'devendera.negi@gmail.com'),
    (SELECT id FROM organizations WHERE slug = 'default-org'),
    (SELECT id FROM roles WHERE code = 'system_admin'),
    true, true, 'active', NOW(), NOW(), NOW()
),
(
    gen_random_uuid(),
    (SELECT id FROM users WHERE email = 'devendera.negi@gmail.com'),
    (SELECT id FROM organizations WHERE slug = 'default-org'),
    (SELECT id FROM roles WHERE code = 'user'),
    true, true, 'active', NOW(), NOW(), NOW()
);
