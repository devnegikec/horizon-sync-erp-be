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

## Permission Codes (Identity)

Granular permissions use the form `resource.action`:

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

If the database was seeded before wildcard permissions were added, the `*.*` permission will not exist. In that case:

1. **New organizations**: Creating an org will still succeed, but the creating user will not get the Owner role (no `*.*` permission row). Manually add a role with full access and assign it to the org creator, or run a migration that inserts the wildcard permission rows from `scripts/seed_data.py` (the block with `*.*`, `system.admin`, `user.*`, `org.*`, `role.*`).
2. **Re-seed**: Alternatively, add a one-off script or migration that inserts only the new permission rows and re-run it.
