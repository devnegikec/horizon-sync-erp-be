# Requirements Document

## Introduction

This feature introduces granular role-based access control (RBAC) for system administrators, replacing the current wildcard permission bypass (`*.*`) with properly scoped system admin roles and permissions. Permissions are broken down to CRUD-level granularity (read, create, update, delete) per domain, with a `_manage` shorthand that grants all four. The system must enforce a strict separation between system-level administration and organization-level user management, ensuring that only a designated Super Admin can create other system admin users, assign system-level roles, and create custom roles. Organization-level users must be prevented from escalating privileges to the system admin domain. The existing platform-level (organization-scoped) roles and permissions logic remains unchanged; this spec only adds the system admin layer.

## Glossary

- **System_Admin_User**: A user with `user_type = "system_admin"` who operates at the platform level, outside any single organization scope.
- **Super_Admin**: A System_Admin_User holding the `system_admin.master` permission, granting the ability to manage other System_Admin_Users, assign system-level roles, and create custom system-level roles.
- **Master_Organization**: The organization with `type = "master"` that serves as the home organization for all System_Admin_Users. System admin roles and user memberships are scoped to this organization.
- **System_Admin_Role**: A Role record with `is_system = true` and `organization_id` set to the Master_Organization's ID, representing a platform-level role that maps to one or more System_Admin_Permissions. All roles (seeded or user-created) are treated equally and can be edited or deleted by a Super_Admin.
- **System_Admin_Permission**: A Permission record scoped to the `system_admin` domain. Each domain (users, organizations, billing, reporting) has CRUD-level permissions (`_read`, `_create`, `_update`, `_delete`) plus a `_manage` shorthand. The `system_admin.master` permission grants access to everything.
- **Manage_Permission**: A shorthand permission (e.g., `system_admin.users_manage`) that is equivalent to holding all four CRUD permissions (`_read`, `_create`, `_update`, `_delete`) for that domain.
- **Organization_User**: A user with `user_type` of `organization_admin`, `user`, or `guest`, scoped to one or more organizations via `UserOrganizationRole` records.
- **Auth_Dependency**: The `get_current_user` function in `core-service/app/dependencies.py` that extracts user identity and permissions from the JWT token.
- **Permission_Checker**: The `require_permission` dependency and `has_permission` utility in `core-service/app/dependencies.py` that enforce RBAC on API endpoints.
- **Identity_Service**: The backend microservice (`identity-service`) that owns user, role, permission, and organization data.
- **Core_Service**: The backend microservice (`core-service`) that hosts admin portal API endpoints and business logic.
- **Admin_App**: The React/TypeScript frontend application (`apps/admin`) used by system administrators.
- **UserOrganizationRole**: The existing mapping model that associates a user with an organization and a role. For System_Admin_Users, this maps them to the Master_Organization with a System_Admin_Role — no new mapping table is needed.

## Requirements

### Requirement 1: Remove Wildcard Permission Bypass for System Admin Users

**User Story:** As a platform security engineer, I want system admin users to be authorized based on their actual assigned permissions, so that granular access control is enforced instead of a blanket wildcard bypass.

#### Acceptance Criteria

1. WHEN a System_Admin_User authenticates, THE Auth_Dependency SHALL resolve the user's permissions from the database via assigned System_Admin_Roles instead of returning the hardcoded `["*.*"]` list.
2. WHEN the Permission_Checker evaluates a System_Admin_User's access, THE Permission_Checker SHALL check the user's actual permission list against the required permission, using the same wildcard matching logic applied to Organization_Users.
3. IF a System_Admin_User does not hold the required permission, THEN THE Permission_Checker SHALL return HTTP 403 Forbidden with a message indicating the missing permission.
4. THE Auth_Dependency SHALL retrieve System_Admin_User permissions by querying UserOrganizationRole (scoped to the Master_Organization) and RolePermission mappings from the Identity_Service.

### Requirement 2: System Admin Role and Permission Data Model with CRUD-Level Granularity

**User Story:** As a platform architect, I want system admin roles and permissions stored in a structured model with CRUD-level granularity per domain, so that system-level RBAC supports fine-grained access control.

#### Acceptance Criteria

1. THE Identity_Service SHALL support System_Admin_Role records where `organization_id` is set to the Master_Organization's ID and `is_system` is true.
2. THE Identity_Service SHALL store System_Admin_User role assignments using the existing `UserOrganizationRole` model, with `organization_id` set to the Master_Organization's ID and `role_id` pointing to a System_Admin_Role.
3. THE Identity_Service SHALL define the following System_Admin_Permissions for the users domain: `system_admin.users_read`, `system_admin.users_create`, `system_admin.users_update`, `system_admin.users_delete`, `system_admin.users_manage`.
4. THE Identity_Service SHALL define the following System_Admin_Permissions for the organizations domain: `system_admin.organizations_read`, `system_admin.organizations_create`, `system_admin.organizations_update`, `system_admin.organizations_delete`, `system_admin.organizations_manage`.
5. THE Identity_Service SHALL define the following System_Admin_Permissions for the billing domain: `system_admin.billing_read`, `system_admin.billing_create`, `system_admin.billing_update`, `system_admin.billing_delete`, `system_admin.billing_manage`.
6. THE Identity_Service SHALL define the following System_Admin_Permissions for the reporting domain: `system_admin.reporting_read`, `system_admin.reporting_create`, `system_admin.reporting_update`, `system_admin.reporting_delete`, `system_admin.reporting_manage`.
7. THE Identity_Service SHALL define the `system_admin.master` permission that grants access to all system admin endpoints regardless of domain or action.
8. WHEN the Permission_Checker evaluates a `_manage` permission (e.g., `system_admin.users_manage`), THE Permission_Checker SHALL treat the Manage_Permission as equivalent to holding all four CRUD permissions (`_read`, `_create`, `_update`, `_delete`) for that domain.
9. WHEN a System_Admin_Role is created, THE Identity_Service SHALL allow linking one or more System_Admin_Permissions to the role via RolePermission records.
10. THE Identity_Service SHALL provide an API endpoint to list all System_Admin_Roles with their associated permissions.

### Requirement 3: Super Admin Exclusive Control Over System Admin User Management

**User Story:** As a Super Admin, I want to be the only user who can create other system admin users and assign system-level roles, so that system-level access is tightly controlled.

#### Acceptance Criteria

1. WHEN a request to create a System_Admin_User is received, THE Core_Service SHALL verify that the requesting user holds the `system_admin.master` permission before proceeding.
2. WHEN a request to assign or modify a System_Admin_Role for a user is received, THE Core_Service SHALL verify that the requesting user holds the `system_admin.master` permission.
3. IF a user without `system_admin.master` permission attempts to create a System_Admin_User, THEN THE Core_Service SHALL return HTTP 403 Forbidden.
4. IF a user without `system_admin.master` permission attempts to assign a System_Admin_Role, THEN THE Core_Service SHALL return HTTP 403 Forbidden.
5. WHEN a Super_Admin creates a System_Admin_User, THE Core_Service SHALL allow assigning one or more System_Admin_Roles to the new user in the same request.

### Requirement 4: Isolation of System Admin Management from Organization-Level Users

**User Story:** As a platform security engineer, I want organization-level users to be completely unable to view, create, or modify system admin users or roles, so that privilege escalation from the organization domain to the system domain is impossible and system admin functionality is invisible to org-level users.

#### Acceptance Criteria

1. WHEN an Organization_User calls the Identity_Service user update endpoint, THE Identity_Service SHALL reject any attempt to set `user_type` to `system_admin` with HTTP 403 Forbidden.
2. WHEN an Organization_User calls the Identity_Service user create endpoint, THE Identity_Service SHALL reject any attempt to set `user_type` to `system_admin` with HTTP 403 Forbidden.
3. THE Identity_Service user update endpoint SHALL validate that only a user with `system_admin.master` permission can change a user's `user_type` to `system_admin`.
4. THE Identity_Service user update endpoint SHALL validate that only a user with `system_admin.master` permission can change a user's `user_type` from `system_admin` to any other type.
5. WHEN an Organization_User calls any system admin role management endpoint (including list/read endpoints), THE Core_Service SHALL return HTTP 403 Forbidden.
6. WHEN an Organization_User calls the Identity_Service user list endpoint, THE Identity_Service SHALL exclude users with `user_type = "system_admin"` from the response.
7. WHEN an Organization_User calls the Identity_Service user detail endpoint for a System_Admin_User, THE Identity_Service SHALL return HTTP 404 Not Found.
8. THE platform-level frontend (platform app, inventory app) SHALL NOT display any system admin roles, permissions, or system admin user type options in any UI component.

### Requirement 5: Granular CRUD-Level Permission Enforcement on Admin Portal Endpoints

**User Story:** As a system admin with limited permissions, I want each admin portal action to require the specific CRUD-level permission for that domain, so that I can only perform the exact operations my role allows.

#### Acceptance Criteria

1. WHEN a System_Admin_User accesses the admin users list endpoint (read), THE Core_Service SHALL require the `system_admin.users_read` permission.
2. WHEN a System_Admin_User accesses the admin users create endpoint, THE Core_Service SHALL require the `system_admin.users_create` permission.
3. WHEN a System_Admin_User accesses the admin users update endpoint, THE Core_Service SHALL require the `system_admin.users_update` permission.
4. WHEN a System_Admin_User accesses the admin users delete endpoint, THE Core_Service SHALL require the `system_admin.users_delete` permission.
5. WHEN a System_Admin_User accesses the admin organizations list endpoint (read), THE Core_Service SHALL require the `system_admin.organizations_read` permission.
6. WHEN a System_Admin_User accesses the admin organizations create endpoint, THE Core_Service SHALL require the `system_admin.organizations_create` permission.
7. WHEN a System_Admin_User accesses the admin organizations update endpoint, THE Core_Service SHALL require the `system_admin.organizations_update` permission.
8. WHEN a System_Admin_User accesses the admin organizations delete endpoint, THE Core_Service SHALL require the `system_admin.organizations_delete` permission.
9. WHEN a System_Admin_User accesses the admin billing read endpoint, THE Core_Service SHALL require the `system_admin.billing_read` permission.
10. WHEN a System_Admin_User accesses the admin billing create endpoint, THE Core_Service SHALL require the `system_admin.billing_create` permission.
11. WHEN a System_Admin_User accesses the admin billing update endpoint, THE Core_Service SHALL require the `system_admin.billing_update` permission.
12. WHEN a System_Admin_User accesses the admin billing delete endpoint, THE Core_Service SHALL require the `system_admin.billing_delete` permission.
13. WHEN a System_Admin_User accesses the admin reporting read endpoint, THE Core_Service SHALL require the `system_admin.reporting_read` permission.
14. WHEN a System_Admin_User accesses the admin reporting create endpoint, THE Core_Service SHALL require the `system_admin.reporting_create` permission.
15. WHEN a System_Admin_User accesses the admin reporting update endpoint, THE Core_Service SHALL require the `system_admin.reporting_update` permission.
16. WHEN a System_Admin_User accesses the admin reporting delete endpoint, THE Core_Service SHALL require the `system_admin.reporting_delete` permission.
17. WHEN a System_Admin_User holds a `_manage` permission for a domain (e.g., `system_admin.users_manage`), THE Permission_Checker SHALL grant access to all CRUD endpoints for that domain.
18. WHEN a System_Admin_User holds the `system_admin.master` permission, THE Permission_Checker SHALL grant access to all `system_admin.*` scoped endpoints.

### Requirement 6: Frontend Isolation of System Admin Options

**User Story:** As a platform developer, I want the frontend to hide system admin user type and role options from organization-level users, so that the UI does not expose privilege escalation paths.

#### Acceptance Criteria

1. WHEN an Organization_User opens the UserDetailModal in edit mode, THE Admin_App SHALL exclude `system_admin` from the USER_TYPE_OPTIONS dropdown.
2. WHEN an Organization_User opens the CreateUserModal, THE Admin_App SHALL exclude `system_admin` from the USER_TYPE_OPTIONS dropdown.
3. WHEN an Organization_User opens the UserDetailModal in edit mode, THE Admin_App SHALL exclude `system_admin` from the ROLE_OPTIONS checkboxes.
4. WHEN an Organization_User opens the CreateUserModal, THE Admin_App SHALL exclude `system_admin` from the ROLE_OPTIONS checkboxes.
5. WHEN a Super_Admin opens the CreateUserModal or UserDetailModal, THE Admin_App SHALL display all USER_TYPE_OPTIONS and ROLE_OPTIONS including system admin values.
6. THE Admin_App SHALL determine the current user's permission level by calling the permissions API and conditionally rendering system admin options based on the response.

### Requirement 7: System Admin Permissions API for Frontend Authorization

**User Story:** As a frontend developer, I want an API endpoint that returns the current system admin user's permissions, so that the Admin_App can conditionally render UI elements based on the user's granular permissions.

#### Acceptance Criteria

1. THE Core_Service SHALL expose a `GET /admin/me/permissions` endpoint that returns the authenticated System_Admin_User's list of system admin permission codes.
2. WHEN a System_Admin_User calls the permissions endpoint, THE Core_Service SHALL return the permission codes derived from the user's assigned System_Admin_Roles.
3. IF a non-system-admin user calls the permissions endpoint, THEN THE Core_Service SHALL return HTTP 403 Forbidden.
4. THE response SHALL include the user's `user_id`, `user_type`, and a list of `permissions` strings.

### Requirement 8: Seed Default Roles and Initial Super Admin User

**User Story:** As a platform operator, I want default system admin roles seeded on deployment with CRUD-level permissions, so that the first system administrator can bootstrap the system and assign granular access.

#### Acceptance Criteria

1. WHEN the Identity_Service database is initialized, THE Identity_Service SHALL create a role named "Super Admin" with the `system_admin.master` permission linked.
2. WHEN the Identity_Service database is initialized, THE Identity_Service SHALL create a role named "System User Manager" with the permissions `system_admin.users_read`, `system_admin.users_create`, `system_admin.users_update`, `system_admin.users_delete` linked.
3. WHEN the Identity_Service database is initialized, THE Identity_Service SHALL create a role named "System Org Manager" with the permissions `system_admin.organizations_read`, `system_admin.organizations_create`, `system_admin.organizations_update`, `system_admin.organizations_delete` linked.
4. WHEN the Identity_Service database is initialized, THE Identity_Service SHALL create a role named "System Billing Manager" with the permissions `system_admin.billing_read`, `system_admin.billing_create`, `system_admin.billing_update`, `system_admin.billing_delete` linked.
5. WHEN the Identity_Service database is initialized, THE Identity_Service SHALL create a role named "System Reports Viewer" with the permissions `system_admin.reporting_read` linked.
6. WHEN the seed process runs, THE Identity_Service SHALL assign the "Super Admin" role to the first existing System_Admin_User if one exists and has no system role assigned.
7. IF the seed process runs multiple times, THEN THE Identity_Service SHALL not create duplicate roles or duplicate role assignments (idempotent operation).
8. ALL seeded roles SHALL be editable and deletable by a Super_Admin, just like any user-created role.

### Requirement 9: Role-Based Permission Pre-Population in System Admin User Creation UI

**User Story:** As a Super Admin creating a new system admin user, I want to select a role and see its associated permissions pre-populated and visible in the UI, so that I understand exactly what access the new user will receive.

#### Acceptance Criteria

1. WHEN a Super_Admin opens the system admin user creation flow, THE Admin_App SHALL display a role assignment step that lists all available System_Admin_Roles.
2. WHEN a Super_Admin selects a role (e.g., "System User Manager"), THE Admin_App SHALL display all associated permissions as pre-selected checkboxes that are visible but not individually editable at the user level (permissions are defined on the role, not per user).
3. THE Admin_App SHALL fetch the list of System_Admin_Roles and their associated permissions from the Identity_Service API to populate the role selection step.
4. WHEN no role is selected, THE Admin_App SHALL display an empty permissions panel with no checkboxes selected.
5. THE Admin_App SHALL allow the Super_Admin to assign one or more System_Admin_Roles to the new user before submitting the creation request.

### Requirement 10: System Admin Role Creation, Editing, and Deletion

**User Story:** As a Super Admin, I want to create, edit, and delete system admin roles with a specific subset of CRUD-level permissions, so that I can tailor access for system admin users whose needs do not match any existing role.

#### Acceptance Criteria

1. WHEN a Super_Admin initiates role creation from the Admin_App, THE Admin_App SHALL display a form with a role name field and a permissions selection panel listing all available System_Admin_Permissions as individually selectable checkboxes.
2. WHEN a Super_Admin submits a role creation request, THE Core_Service SHALL verify that the requesting user holds the `system_admin.master` permission.
3. IF a user without `system_admin.master` permission attempts to create a role, THEN THE Core_Service SHALL return HTTP 403 Forbidden.
4. WHEN a role is created, THE Identity_Service SHALL store the role with `is_system = true` and `organization_id` set to the Master_Organization's ID.
5. THE Identity_Service SHALL link the selected System_Admin_Permissions to the new role via RolePermission records.
6. WHEN a role is saved, THE Admin_App SHALL immediately make it available for assignment in the role selection list alongside all other roles.
7. WHEN a Super_Admin edits an existing role, THE Admin_App SHALL allow modifying the role name and adding or removing individual permissions.
8. WHEN a Super_Admin deletes a role, THE Core_Service SHALL verify that the requesting user holds the `system_admin.master` permission and remove the role and its RolePermission records.
9. THE Identity_Service SHALL provide API endpoints for creating, updating, listing, and deleting System_Admin_Roles.

### Requirement 11: Admin App Navigation and UI Element Visibility Based on Granular Permissions

**User Story:** As a system admin user with limited permissions, I want the Admin_App to show only the navigation items and action buttons that my permissions allow, so that I have a clean interface without inaccessible features.

#### Acceptance Criteria

1. WHEN a System_Admin_User logs into the Admin_App, THE Admin_App SHALL fetch the user's permissions from the `GET /admin/me/permissions` endpoint and store them in the application state.
2. WHEN a System_Admin_User does not hold any `system_admin.users_*` permission, THE Admin_App SHALL hide the "Users" navigation item from the sidebar.
3. WHEN a System_Admin_User holds `system_admin.users_read` but not `system_admin.users_create`, THE Admin_App SHALL display the Users page but hide the "Create User" button.
4. WHEN a System_Admin_User does not hold any `system_admin.organizations_*` permission, THE Admin_App SHALL hide the "Organizations" navigation item from the sidebar.
5. WHEN a System_Admin_User does not hold any `system_admin.billing_*` permission, THE Admin_App SHALL hide the "Billing" navigation item from the sidebar.
6. WHEN a System_Admin_User does not hold any `system_admin.reporting_*` permission, THE Admin_App SHALL hide the "Reports" navigation item from the sidebar.
7. WHEN a System_Admin_User holds the `system_admin.master` permission, THE Admin_App SHALL display all navigation items and action buttons.
