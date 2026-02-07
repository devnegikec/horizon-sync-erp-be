---
name: ""
overview: ""
todos: []
isProject: false
---

# Wildcard Permissions, Org Owner, and System Administrators

## Current Implementation Summary

- **Permissions**: Stored as `Permission.code` (e.g. `user.read`, `role.manage`) with exact-match checks in identity and core-service.
- **System admin**: Currently `role.manage` or `user_type == "system_admin"` used for cross-org listing and bypasses.
- **Owner**: `Organization.owner_id` set on create but not used for authorization.

---

## 1. Wildcard Permission Model

Support codes like `user.*`, `org.*`, `role.*`, `warehouse.*`, and `*.*`. At check time, grant required permission if user has: exact match, or `resource.*`, or `*.*`. Implement `has_permission(permissions, required)` in identity and core-service; seed wildcard permission rows.

---

## 2. Org Owner (First User = Full Access in That Org)

**Recommended**: On org create, create an "Owner" role for that org with permission `*.*` and assign the creating user to it. No special-case `owner_id` in auth. Owner = user with Owner role.

---

## 3. System Administrators: One-Org-Per-Session (Revised)

**Chosen approach**: System users do **not** get cross-org permission. They get access to **one organization at a time**. The user chooses (or is assigned) an org at login; the token/session is scoped to that org. To work in another org, they must **switch context** (logout and login with another org, or use an **org switcher** that issues a new token for the selected org).

### Why this approach

- **Simpler security**: No cross-org bypass logic in core-service. Every request is scoped to `organization_id` from the token; no special `is_system_admin` branch for "allow any org."
- **Clear audit**: Each action is tied to a single org. Logs and audit trails are unambiguous.
- **Smaller blast radius**: A compromised token gives access only to the org selected at login, not all orgs.
- **Familiar UX**: Aligns with multi-tenant products where you pick workspace/org at login.

### How it works

1. **Login**: When a system admin (or any user in multiple orgs) logs in, they either:

- Select one org from a list (e.g. dropdown), or
- Are given a default/primary org.
  Identity issues an **access token scoped to that org** (e.g. `organization_id` in token claims and/or returned by `/me`).

1. **Requests**: Identity and core-service use the token’s `organization_id` (or `/me`’s `organization_id`) for all data scope. No "system admin can access any org" bypass.
2. **Switching org**: To work in another org, the user:

- **Option A (recommended)**: Uses an **org switcher** in the app: they pick another org, the client calls an identity endpoint (e.g. "switch context" or "re-token for org") with the new org ID; identity validates the user (and that they are allowed to enter that org) and returns a **new access token** scoped to the selected org. No full logout or password re-entry.
- **Option B**: Logs out and logs in again, selecting the other org at login. Same one-org-per-session guarantee, more friction.

### Who can "enter" which org

- **Normal users**: Can only select orgs they belong to (they have a role in that org).
- **System administrators**: Can be allowed to select **any org** (not only those they’re a member of). In that case:
  - At login or org-switch, identity checks that the user has a "system admin" capability (e.g. permission `system.admin` or a dedicated system role).
  - Identity then issues a token for the **chosen org** with permissions that apply in that org. Options:
    - **A**: System admin has a role in every org (e.g. "System Viewer" per org); switching org just switches which org’s role is active.
    - **B**: System admin has no membership in most orgs; when they select an org, identity treats them as having a fixed set of permissions **in that org for this session** (e.g. read-only or full admin). That is a "virtual" or "impersonation" context: no need to create a role in every org.

Option B is simpler for "one system admin, many orgs": no per-org role assignment; backend allows "system admin can request token for any org" and applies a standard permission set for that session.

### Implementation outline

- **Identity**:
  - Login (and optional org-switch endpoint) accepts `organization_id` when the user is a system admin or has multiple orgs. Validate that either the user is in that org or the user is a system admin (permission or role). Issue token with chosen `organization_id` in payload and/or ensure `/me` returns that `organization_id` and permissions for that context.
  - Remove or avoid relying on "cross-org" behavior: no API that returns data from all orgs in one call for system admin; they use one org per session.
- **Core-service**: No change to org scoping: always use `organization_id` from token/`/me`. No `is_system_admin` bypass for org scope. Optional: keep `is_system_admin` only for non-org-scoped actions (e.g. future system-wide config) if ever needed.
- **Optional**: Add an identity endpoint like `POST /auth/switch-org` (or include in login) that accepts `organization_id` and returns a new access token for that org when the user is allowed (member or system admin).

### Summary for system users

| Aspect                   | One-org-per-session (chosen)                                                      |
| ------------------------ | --------------------------------------------------------------------------------- |
| Scope                    | One org per token/session                                                         |
| Switch org               | Logout and login with other org, or **org switcher** (new token for selected org) |
| Cross-org in one request | No; not needed                                                                    |
| Core-service             | Always filter by token’s `organization_id`; no special system-admin org bypass    |
| Best practice            | Prefer **org switcher** over full logout for better UX                            |

---

## 4. Best Practices and Safeguards

- **Full access (_._)**: Use audit logging, MFA for _._/system.admin, and prefer resource wildcards (e.g. `user.*`) over `*.*` where possible. Reserve `*.*` for org owner and minimal super-admin use.
- **System admin**: One-org-per-session reduces risk; org switcher improves UX without changing the security model.

---

## 5. Implementation Order

1. Wildcard matching in identity and core-service; seed wildcard permissions.
2. Owner role with `*.*` on org create.
3. **System admins**: Login (and optional org-switch) with org selection; token scoped to one org; no cross-org bypass in core-service. Implement "system admin can request token for any org" and, if desired, org-switcher endpoint.
4. Tests and docs for wildcards, owner, and one-org-per-session system admin.
