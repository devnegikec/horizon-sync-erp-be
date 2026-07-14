# Implementation Plan: Admin Granular Roles & Permissions

## Overview

Replace the hardcoded `["*.*"]` wildcard permission bypass for system admin users with a proper RBAC system. Implement CRUD-level granular permissions (`system_admin.{domain}_{action}`) across four domains, `_manage` shorthand expansion, `system_admin.master` super-permission, granular endpoint guards, system admin user isolation, role CRUD endpoints, a seed script, and frontend permission-aware rendering.

## Tasks

- [x] 1. Update authorization constants and enhance permission resolution logic
  - [x] 1.1 Replace coarse-grained system admin constants in `core-service/app/core/authorization.py`
    - Remove the existing `SYSTEM_ADMIN_MASTER`, `SYSTEM_ADMIN_USERS`, `SYSTEM_ADMIN_ORGANIZATIONS`, `SYSTEM_ADMIN_BILLING`, `SYSTEM_ADMIN_REPORTING` constants
    - Add CRUD-level constants for all 4 domains: `SYSTEM_ADMIN_USERS_READ`, `_CREATE`, `_UPDATE`, `_DELETE`, `_MANAGE`; same for organizations, billing, reporting; plus `SYSTEM_ADMIN_MASTER`
    - _Requirements: 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 1.2 Update `has_permission` in `core-service/app/dependencies.py` to support `_manage` expansion and `system_admin.master`
    - Add `system_admin.master` check: if required permission starts with `system_admin.` and user has `system_admin.master`, grant access
    - Add `_manage` expansion: if required permission is `system_admin.{domain}_{action}`, check if user has `system_admin.{domain}_manage`
    - Keep existing `resource.*` wildcard matching
    - Remove `*.*` wildcard matching from `has_permission`
    - _Requirements: 2.7, 2.8, 5.17, 5.18_

  - [x] 1.3 Remove the system admin `*.*` bypass in `core-service/app/dependencies.py` `get_current_user`
    - Replace the `if user_type == "system_admin": return CurrentUser(..., permissions=["*.*"])` block
    - For system admin users, call `_get_user_org_and_permissions(token)` to fetch real permissions from identity-service `/me`
    - Set `organization_id` to the master org ID returned from `/me`
    - _Requirements: 1.1, 1.4_

  - [x] 1.4 Remove the system admin bypass in `require_permission` in `core-service/app/dependencies.py`
    - Remove the `if current_user.user_type == "system_admin": return current_user` shortcut
    - Rely entirely on `has_permission` which now understands `system_admin.master` and `_manage`
    - _Requirements: 1.2, 1.3_

  - [x] 1.5 Remove the system admin `*.*` override in `identity-service/app/dependencies.py` `get_current_user`
    - Remove the `if user.user_type == UserType.SYSTEM_ADMIN: permissions = ["*.*"]` block
    - Let `_get_user_permissions(db, user.id)` run for system admin users the same as org users
    - _Requirements: 1.1, 1.4_

  - [x] 1.6 Remove the system admin bypass in `identity-service/app/dependencies.py` `require_permission`
    - Remove the `if current_user.user_type == UserType.SYSTEM_ADMIN: return current_user` shortcut
    - Remove the `if "*.*" in current_user.permissions: return current_user` check
    - _Requirements: 1.2, 1.3_

- [x] 2. Checkpoint — Verify permission resolution changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Apply granular `require_permission` guards on all admin endpoints
  - [x] 3.1 Update `core-service/app/api/v1/endpoints/admin/users.py` endpoint guards
    - Replace `require_admin` with `require_permission(SYSTEM_ADMIN_USERS_READ)` on GET endpoints
    - Replace `require_admin` with `require_permission(SYSTEM_ADMIN_USERS_CREATE)` on POST endpoint
    - Replace `require_admin` with `require_permission(SYSTEM_ADMIN_USERS_UPDATE)` on PATCH endpoint
    - Import the new constants from `app.core.authorization`
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 3.2 Update `core-service/app/api/v1/endpoints/admin/organizations.py` endpoint guards
    - Replace `require_admin` with `require_permission(SYSTEM_ADMIN_ORGANIZATIONS_READ)` on GET endpoints
    - Replace `require_admin` with `require_permission(SYSTEM_ADMIN_ORGANIZATIONS_CREATE)` on POST endpoint
    - Replace `require_admin` with `require_permission(SYSTEM_ADMIN_ORGANIZATIONS_UPDATE)` on PATCH endpoint
    - _Requirements: 5.5, 5.6, 5.7, 5.8_

  - [x] 3.3 Update `core-service/app/api/v1/endpoints/admin/billing.py` endpoint guards
    - Replace `require_permission("system_admin.billing")` with the appropriate CRUD-level constant (e.g., `SYSTEM_ADMIN_BILLING_CREATE` for POST, `SYSTEM_ADMIN_BILLING_READ` for GET)
    - Replace `require_permission("system_admin.org_manager")` on `get_customer_organizations` and `assign_customer_to_master` with `SYSTEM_ADMIN_ORGANIZATIONS_READ` / `SYSTEM_ADMIN_ORGANIZATIONS_UPDATE` respectively
    - _Requirements: 5.9, 5.10, 5.11, 5.12_

  - [x] 3.4 Update remaining admin endpoints (dashboard, invoices, payments, activity_logs, audit_logs, payment_reminders) with appropriate granular guards
    - Dashboard: `SYSTEM_ADMIN_REPORTING_READ`
    - Invoices read: `SYSTEM_ADMIN_BILLING_READ`, invoices create: `SYSTEM_ADMIN_BILLING_CREATE`
    - Payments read: `SYSTEM_ADMIN_BILLING_READ`
    - Activity/Audit logs: `SYSTEM_ADMIN_REPORTING_READ`
    - Payment reminders: `SYSTEM_ADMIN_BILLING_UPDATE`
    - _Requirements: 5.13, 5.14, 5.15, 5.16_

- [x] 4. Implement system admin user isolation in identity-service
  - [x] 4.1 Add isolation filters to `identity-service/app/api/v1/endpoints/users.py`
    - In `list_users`: add `.filter(User.user_type != UserType.SYSTEM_ADMIN)` when caller is not a system admin (check caller's permissions for `system_admin.master`)
    - In `get_user`: return 404 if target user is `system_admin` and caller does not hold `system_admin.master`
    - _Requirements: 4.6, 4.7_

  - [x] 4.2 Add `user_type` escalation guards to `identity-service/app/api/v1/endpoints/users.py`
    - In `create_user`: reject `user_type=system_admin` in the payload unless caller holds `system_admin.master`
    - In `update_user`: reject changing `user_type` to `system_admin` or from `system_admin` to another type unless caller holds `system_admin.master`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 5. Implement `GET /admin/me/permissions` endpoint and role CRUD endpoints
  - [x] 5.1 Add `GET /admin/me/permissions` endpoint in core-service
    - Create the endpoint in the admin router (e.g., in `core-service/app/api/v1/endpoints/admin/system.py` or a new file)
    - Guard with `require_admin` (any system admin can call it)
    - Return `{ user_id, user_type, permissions }` from `current_user`
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 5.2 Create `core-service/app/api/v1/endpoints/admin/roles.py` with role CRUD endpoints
    - `GET /admin/roles` — list system admin roles with permissions, guarded by `system_admin.master`
    - `POST /admin/roles` — create role with permission links, guarded by `system_admin.master`
    - `PATCH /admin/roles/{id}` — update role name/permissions, guarded by `system_admin.master`
    - `DELETE /admin/roles/{id}` — delete role and RolePermission records, guarded by `system_admin.master`
    - `GET /admin/permissions` — list all available system admin permissions, guarded by `system_admin.master`
    - Proxy to identity-service or query identity DB directly (same pattern as existing admin endpoints)
    - _Requirements: 2.9, 2.10, 10.1, 10.2, 10.3, 10.4, 10.5, 10.8, 10.9_

  - [x] 5.3 Register the roles router in `core-service/app/api/v1/endpoints/admin/__init__.py`
    - Import and include the roles router with prefix `/roles`
    - _Requirements: 2.10, 10.9_

- [x] 6. Create seed script for default permissions, roles, and role-permission links
  - [x] 6.1 Create seed script in identity-service (e.g., `identity-service/scripts/seed_system_admin_roles.py` or add to existing seed service)
    - Insert 21 system admin permission records (4 domains × 5 perms + 1 master) using `INSERT ... ON CONFLICT DO NOTHING` or check-before-insert
    - Create 5 default roles: Super Admin, System User Manager, System Org Manager, System Billing Manager, System Reports Viewer
    - Link permissions to roles via RolePermission records
    - Assign "Super Admin" role to the first existing `system_admin` user via UserOrganizationRole (scoped to master org)
    - Ensure idempotency — safe to run multiple times
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [x] 7. Checkpoint — Verify backend changes end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Create frontend permission types and PermissionsContext
  - [x] 8.1 Create `apps/admin/src/app/types/permissions.ts`
    - Define `SYSTEM_ADMIN_PERMISSIONS` constant object with all 21 permission codes
    - Export `SystemAdminPermission` type
    - Export `hasPermission(userPermissions, required)` helper with master check and `_manage` expansion
    - Export `hasAnyPermissionForDomain(userPermissions, domain)` helper
    - _Requirements: 11.1_

  - [x] 8.2 Create `apps/admin/src/app/contexts/PermissionsContext.tsx`
    - On login/mount, fetch `GET /admin/me/permissions` and store permissions in React Context
    - Expose `hasPermission(code)` and `hasAnyPermission(codes[])` helpers via context
    - Handle loading and error states
    - _Requirements: 11.1, 7.1_

  - [x] 8.3 Update `apps/admin/src/app/hooks/usePermissions.ts` to use the new PermissionsContext
    - Wire the existing `usePermissions` hook to the new context so the Sidebar and other consumers work seamlessly
    - _Requirements: 11.1_

- [x] 9. Update frontend conditional rendering based on granular permissions
  - [x] 9.1 Update `apps/admin/src/app/components/Sidebar.tsx` nav items with granular permission codes
    - "Users" → requires any `system_admin.users_*`
    - "Organizations" → requires any `system_admin.organizations_*`
    - "Billing" → requires any `system_admin.billing_*`
    - "Reports" / "Audit Logs" → requires any `system_admin.reporting_*`
    - Replace old permission strings like `system_admin.billing`, `system_admin.org_manager`, `*.*`
    - _Requirements: 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

  - [x] 9.2 Add action-level permission guards on admin pages
    - On UsersPage: hide "Create User" button if user lacks `system_admin.users_create`; hide edit/delete actions based on `_update`/`_delete`
    - On OrganizationsPage: hide "Create Organization" button if user lacks `system_admin.organizations_create`
    - Similar pattern for billing and reporting pages
    - _Requirements: 11.3_

- [x] 10. Implement frontend isolation of system admin options
  - [x] 10.1 Update `CreateUserModal` to filter `USER_TYPE_OPTIONS` and `ROLE_CHECKBOX_OPTIONS`
    - Accept a `permissions` or `isSuperAdmin` prop
    - If user does not hold `system_admin.master`, filter out `system_admin` from `USER_TYPE_OPTIONS` and `ROLE_CHECKBOX_OPTIONS`
    - _Requirements: 6.2, 6.4, 6.5_

  - [x] 10.2 Update `UserDetailModal` to filter `USER_TYPE_OPTIONS` and `ROLE_OPTIONS`
    - Same filtering logic as CreateUserModal
    - If user does not hold `system_admin.master`, exclude `system_admin` values
    - _Requirements: 6.1, 6.3, 6.5_

- [x] 11. Implement frontend role assignment UI and role CRUD UI
  - [x] 11.1 Add role selection step to system admin user creation flow
    - Fetch `GET /admin/roles` to get available system admin roles
    - Display roles as selectable cards/radio buttons
    - On role selection, display associated permissions as read-only checkboxes
    - Allow selecting multiple roles
    - Submit role IDs alongside user creation payload
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 11.2 Create role CRUD UI for Super Admins
    - Add a "Roles" page or section accessible from the sidebar (guarded by `system_admin.master`)
    - Role creation form: name field + permissions selection panel with checkboxes for all system admin permissions
    - Role editing: modify name and add/remove permissions
    - Role deletion with confirmation
    - Fetch available permissions from `GET /admin/permissions`
    - _Requirements: 10.1, 10.2, 10.3, 10.5, 10.6, 10.7, 10.8_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- The design does not use pseudocode — Python (backend) and TypeScript (frontend) are used directly
- No schema migrations needed — the existing `Permission`, `Role`, `RolePermission`, and `UserOrganizationRole` models support the new permission codes
