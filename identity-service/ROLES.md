# Roles and Permissions

## All Possible Roles

Roles are scoped to an organization (except when used for system-wide templates in seed). A user can have different roles in different organizations.

| Role code        | Name                       | Scope   | Description                                                                                                                                         |
| ---------------- | -------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **system_admin** | System Administrator       | Per-org | Full access in the chosen org; can be granted `*.*` or all granular permissions. Used for platform support; one org per session (login/switch org). |
| **org_admin**    | Organization Administrator | Per-org | Organization and user management in that org (org.\*, user read/update).                                                                            |
| **user**         | User                       | Per-org | Standard user; basic read (user.read, org.read). Default role for new users.                                                                        |
| **owner**        | Organization Owner         | Per-org | Created automatically when an organization is created. Assigned to the user who created the org. Has full access in that org (`*.*`). One per org.  |

### Summary

- **System Administrator** – Intended for support/platform admins. Access is one org at a time (select org at login or via org switcher). No cross-org in a single request.
- **Organization Administrator** – Manages one org: org settings and users (read/update).
- **User** – Normal member with minimal read access; assign additional permissions as needed.
- **Owner** – The first user who created the org; has all permissions in that org via `*.*`. Not created by seed; created when `POST /organizations` is called.

---

## Wildcard Permissions

Permissions can be granular (`user.read`, `warehouse.create`) or wildcards:

| Code           | Meaning                                                                                            |
| -------------- | -------------------------------------------------------------------------------------------------- |
| `*.*`          | Full access (all resources and all actions).                                                       |
| `user.*`       | All actions on user resource (user.read, user.create, user.update, user.delete, user.manage).      |
| `org.*`        | All actions on organization.                                                                       |
| `role.*`       | All actions on roles.                                                                              |
| `system.admin` | System administrator capability (e.g. can select any org at login; used with one-org-per-session). |

Other resource wildcards (e.g. `warehouse.*`, `item.*`) can be added to the permissions table and used the same way: they grant every action for that resource.

### Matching Rules

When checking a required permission (e.g. `user.read`):

1. **Exact match** – User has `user.read`.
2. **Resource wildcard** – User has `user.*`.
3. **Full wildcard** – User has `*.*`.

---

## Permissions Table: resource, action, and code

The `permissions` table has (among others) **resource**, **action**, and **code** columns. Authorization in the app uses **code** only; resource and action are for display, filtering, and grouping.

### Mapping (resource + action → code)

The **code** is the string used in `require_permission(..., code)` and in the list returned by `/me` (user’s permissions). Format: `code = "{prefix}.{action}"` where:

- For **user**: prefix = `"user"` (same as resource value).
- For **organization**: prefix = `"org"` (short form; resource value is `"organization"`).
- For **role**: prefix = `"role"` (same as resource value).

| resource (column) | action (column) | code (used in app) |
| ----------------- | --------------- | ------------------ |
| user              | create          | user.create        |
| user              | read            | user.read          |
| user              | update          | user.update        |
| user              | delete          | user.delete        |
| user              | manage          | user.manage        |
| organization      | create          | org.create         |
| organization      | read            | org.read           |
| organization      | update          | org.update         |
| organization      | delete          | org.delete         |
| organization      | manage          | org.manage         |
| role              | create          | role.create        |
| role              | read            | role.read          |
| role              | update          | role.update        |
| role              | delete          | role.delete        |
| role              | manage          | role.manage        |

So:

- **resource** and **action** match the enums (`ResourceType`, `ActionType`); stored in DB as `user`, `organization`, `role` and `create`, `read`, `update`, `delete`, `manage`.
- **code** must be unique and is what the API checks. For organization we use **org** in the code, not **organization**, so all endpoints use `"org.read"`, `"org.create"`, etc.

Rule to derive **code** from (resource, action):

- If `resource == "organization"` then use prefix `"org"`, else use `resource` as prefix.
- `code = f"{prefix}.{action}"`.

---

## Permission Codes (Identity)

Granular permissions use the form `resource.action` (with **org** for organization):

- **user**: user.create, user.read, user.update, user.delete, user.manage
- **org**: org.create, org.read, org.update, org.delete, org.manage
- **role**: role.create, role.read, role.update, role.delete, role.manage

Core-service uses additional resources (e.g. warehouse, item, customer, supplier, invoice, payment). Those are enforced in core-service; identity can seed matching permission rows and/or wildcards (e.g. `warehouse.*`) as needed.

---

## Safeguards

- **Full access (`*.*`)**: Prefer resource wildcards (`user.*`, `warehouse.*`) where possible. Use `*.*` only for Owner and minimal super-admin roles. Consider MFA and audit logging for any role with `*.*`.
- **System admins**: One-org-per-session; no cross-org data in one request. Use org switcher or re-login to change org.
- **Owner**: Automatically assigned on org create; no need to create an Owner role manually for existing orgs unless backfilling.

---

## Existing Databases

If the database was seeded before wildcard permissions were added, the `*.*` permission may not exist. When a user creates a new organization, the organization service now **creates the `*.*` permission** if it is missing and then assigns the Owner role to the creator, so no manual step is required for new orgs. To have wildcards (e.g. `user.*`, `org.*`) available for role assignment without creating an org first, run a migration or seed that inserts the wildcard permission rows from `scripts/seed_data.py`.
