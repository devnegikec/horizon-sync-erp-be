# Multi-tenant isolation (organization boundaries)

Every user belongs to one or more organizations. **Permission codes are granted
per organization**, but the JWT context used to expose them was a flat union of
all organizations — so a role held in organization *A* authorized work in
organization *B*. This document describes the guard model that closes that gap.

## Model

`CurrentUser` (identity-service `app/dependencies.py`) now carries:

| Field | Meaning |
|---|---|
| `permissions` | Union of every organization's grants. **Do not use for tenant-scoped operations.** |
| `organization_permissions` | `{org_id: [permission codes]}` — an entry exists for **every active membership**, so "member with no role" (`[]`) is distinguishable from "not a member" (missing key). |
| `organization_ids` | The keys of the map above. |
| `is_member_of(org_id)` | Active membership check. |
| `permissions_in(org_id)` | Grants **inside** that organization only. |

## Guards (`app/core/authorization.py`)

| Guard | Use for |
|---|---|
| `require_organization_permission(user, org_id, code)` | An endpoint that knows the target organization (path/query/body). Enforces membership **and** the permission inside that org. |
| `require_any_organization_permission(user, org_id, [codes])` | Same, but any one of several codes is enough (e.g. `user.invite` **or** `invitation.create`). |
| `require_shared_organization_permission(db, user, target_user_id, code)` | Endpoints keyed by a **user id** only. Requires a shared organization (else `404`, so existence is not leaked) **and** the grant in one of those organizations. |
| `require_permission(codes, code)` | Platform-level (`system_admin.*`) checks, or where the list has already been scoped to one organization. |

Platform admins (explicit `system_admin.*`) bypass tenant scoping by design.

## Where it is enforced today

| Area | Endpoint(s) |
|---|---|
| Users | list (orgs filtered by `user.read`), get, create, update, delete, `/{id}/roles`, `/{id}/permissions` |
| Roles | list, create, update, delete, permissions read/assign/remove/bulk, role users |
| Organizations | update, delete; the platform-wide billing backfill now requires **`system_admin.master`** (was `*.*`, which any org owner holds) |
| Invitations | create, list, get, cancel, resend (public token endpoints untouched) |
| Workers | `require_worker_manager` evaluates `warehouse.manage` in the caller's target organization |
| Dashboard layout | already membership-guarded |

## Rules for new endpoints

1. If the request carries an `organization_id`, call `require_organization_permission`.
2. If it carries only a resource id, load the row **then** call
   `require_organization_permission(row.organization_id, ...)`; on a miss return
   `404`, not `403`, so ids cannot be probed.
3. If it carries only a `user_id`, use `require_shared_organization_permission`.
4. Never filter or authorize with `current_user.permissions` on tenant data.
5. Always include `organization_id == <org>` in the query itself — the guard is
   not a substitute for a scoped `WHERE`.
6. Wrap broad `except Exception` handlers with `except HTTPException: raise`
   first, otherwise a deliberate `403` degrades into `500`.

## Known remaining work

- `core-service`: business data (invoices, items, stock, orders, …) is filtered
  by `current_user.organization_id`, but there is no per-organization RBAC there —
  permissions still come from the identity-service `/me` union. An audit of every
  `db.query(Model).filter(Model.id == ...)` without an org predicate is pending.
- `search-service`: verify every index query carries the tenant filter.
