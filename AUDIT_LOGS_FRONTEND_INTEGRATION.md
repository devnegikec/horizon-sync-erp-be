# Audit Logs — Frontend Integration Notes

This document tells the frontend team how to wire the audit-trail UI to the
core-service backend. It covers authentication, the three endpoints, exact
request/response shapes (TypeScript), filter semantics, and UI recommendations.

---

## 1. Base facts

| Item | Value |
|---|---|
| Base URL | `${API_BASE_URL}/api/v1` |
| Auth | `Authorization: Bearer <JWT>` (identity-service access token) |
| Required permission | `system_admin.reporting_read` (system admin + organization admin bypass) |
| Content type | `application/json` |

All three endpoints are read-only `GET` and return `401` without a valid token,
`403` without the reporting permission, and `400` for invalid filter values
(module names, UUIDs, dates).

---

## 2. Endpoints

### 2.1 List audit logs (paginated, filterable)

```
GET /api/v1/admin/audit-logs
```

Query parameters (all optional except pagination defaults):

| Param | Type | Notes |
|---|---|---|
| `page` | int | 1-based, default `1` |
| `page_size` | int | default `20`, max `100` |
| `organization_id` | UUID | cross-org for system admins |
| `table_name` | string | exact table name, e.g. `items`, `asn_orders` |
| `record_id` | UUID | history of one record |
| `user_id` | UUID | acting user |
| `action` | string | `CREATE` \| `UPDATE` \| `DELETE` |
| `role` | string | user role captured at write time (see §5) |
| `module` | string | business module (see §4) — expands server-side to a `table_name IN (...)` filter |
| `date_from` / `date_to` | ISO-8601 datetime | inclusive range on `created_at` |
| `changed_field` | string | field name present in `changed_fields` |

Response:

```json
{
  "audit_logs": [ /* AuditLogListItem, see §3 */ ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 452,
    "total_pages": 23,
    "has_next": true,
    "has_prev": false
  }
}
```

### 2.2 Module catalog (for the module filter dropdown)

```
GET /api/v1/admin/audit-logs/modules
```

Response:

```json
{
  "modules": [
    { "module": "Inventory", "tables": ["items", "stock_levels", "..."] },
    { "module": "WMS",      "tables": ["asn_orders", "bins", "..."] },
    { "module": "QSeal",    "tables": ["qr_products", "..."] },
    { "module": "Users",    "tables": ["warehouse_users"] },
    { "module": "Roles",    "tables": [] }
  ]
}
```

> This list is the source of truth for the module filter. It currently exposes
> `Inventory`, `WMS`, `QSeal`, `Users`, `Roles`. See §4 for the
> revenue/settings caveat.

### 2.3 Record change history

```
GET /api/v1/admin/audit-logs/{record_id}/history?table_name=items&page=1&page_size=20
```

- `record_id` is a path param (UUID).
- `table_name` is a **required** query param.

Response:

```json
{
  "record_id": "…",
  "table_name": "items",
  "history": [ /* AuditLogDetail: AuditLogListItem + change_diff */ ],
  "pagination": { /* same shape as §2.1 */ }
}
```

---

## 3. TypeScript types

```ts
export type AuditAction = "CREATE" | "UPDATE" | "DELETE";

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number | null;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface AuditLogListItem {
  id: string;
  user_id: string | null;
  organization_id: string | null;
  action: AuditAction;
  role: string | null;          // user role at write time (JWT user_type)
  module: string | null;        // derived from table_name (see §4)
  table_name: string;
  record_id: string;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  changed_fields: string[] | null;
  ip_address: string | null;
  created_at: string;           // ISO 8601
  // Resolved user / org info (from identity DB):
  user_name: string | null;         // "First Last"
  user_email_address: string | null; // actual email — USE THIS for email
  user_email: string | null;        // ⚠ legacy: holds display name (name || email)
  organization_name: string | null;
}

export interface ChangeDiffEntry {
  field: string;
  old_value: unknown;
  new_value: unknown;
}

export interface AuditLogDetail extends AuditLogListItem {
  change_diff: ChangeDiffEntry[] | null;
}

export interface AuditLogListResponse {
  audit_logs: AuditLogListItem[];
  pagination: PaginationMeta;
}

export interface AuditLogHistoryResponse {
  record_id: string;
  table_name: string;
  history: AuditLogDetail[];
  pagination: PaginationMeta;
}

export interface AuditModuleInfo {
  module: string;
  tables: string[];
}

export interface AuditModuleListResponse {
  modules: AuditModuleInfo[];
}

export interface AuditLogListParams {
  organization_id?: string;
  table_name?: string;
  record_id?: string;
  user_id?: string;
  action?: AuditAction;
  role?: string;
  module?: string;
  date_from?: string; // ISO 8601
  date_to?: string;   // ISO 8601
  changed_field?: string;
  page?: number;
  page_size?: number;
}
```

> **`user_email` quirk:** the backend currently returns the user's **display
> name** in `user_email` (with email as fallback). Use `user_name` for the name
> and `user_email_address` for the email. Avoid relying on `user_email`.

---

## 4. Module mapping

- The backend derives `module` per row from `table_name` using a fixed map in
  `app/core/audit_modules.py`.
- `GET /modules` returns the modules currently enabled for filtering.
- Filtering by `module` expands server-side to `table_name IN (…)`.

**Current enabled modules:** `Inventory`, `WMS`, `QSeal`, `Users`, `Roles`.

**Caveat:** `Revenue`, `Settings` and `Other` are currently commented out in
the backend map. Rows whose tables are not in the active map (e.g. invoices,
payments, settings tables) still come back, but with `module: "Other"` — and
`Other` is **not** currently filterable (`?module=Other` returns `400`). When
the backend re-enables those modules, re-fetch `/modules` and they will appear
automatically; no frontend change is needed.

---

## 5. Filter value reference

| Filter | Values |
|---|---|
| `action` | `CREATE`, `UPDATE`, `DELETE` |
| `role` | `system_admin`, `organization_admin`, `user`, `warehouse_worker`, … (whatever the identity service stores in the JWT `user_type` claim) |
| `module` | from `GET /modules` (currently Inventory / WMS / QSeal / Users / Roles) |

Historic rows written before role capture shipped have `role: null` — don't
render these as empty filters crashing; just show "—" and keep the role filter
as an explicit "any role" vs. "no role recorded" state if needed.

---

## 6. API client example

Mirrors the project's central `apiRequest` pattern
(`params: {}` object, generic return type):

```ts
import { apiRequest } from "@/api/core";

export const auditLogService = {
  list(token: string, params: AuditLogListParams) {
    return apiRequest<AuditLogListResponse>("/admin/audit-logs", token, {
      params,
    });
  },

  modules(token: string) {
    return apiRequest<AuditModuleListResponse>(
      "/admin/audit-logs/modules",
      token,
    );
  },

  history(
    token: string,
    recordId: string,
    tableName: string,
    page = 1,
    pageSize = 20,
  ) {
    return apiRequest<AuditLogHistoryResponse>(
      `/admin/audit-logs/${recordId}/history`,
      token,
      { params: { table_name: tableName, page, page_size: pageSize } },
    );
  },
};
```

---

## 7. UI wiring recommendations

1. **Filter bar**
   - Module (dropdown ← `GET /modules`)
   - Action (CREATE / UPDATE / DELETE)
   - Role (text or dropdown; populate from known values, allow free text)
   - User (resolved to `user_id` — see note below)
   - Date range (`date_from`/`date_to`, ISO 8601)
   - Table name (advanced, free text)
   - Reset button that clears all params.

2. **Table columns** — `created_at`, `action` (badge), `module` (chip),
   `table_name`, `record_id`, user display (`user_name`), `role`, `ip_address`,
   and a "view changes" action.

3. **Row → detail**
   - For the change breakdown use the list row's `old_values` / `new_values` /
     `changed_fields` directly (no extra call needed for a quick diff).
   - For the full timeline of one record, open the history drawer with
     `GET /audit-logs/{record_id}/history?table_name=…`, which also provides the
     computed `change_diff` per entry.

4. **Pagination** — use `pagination.total_pages`, `has_next`, `has_prev`;
   clamp `page_size` to ≤ 100.

5. **User filtering caveat** — there is no "search users by name" endpoint in
   this API; `user_id` is the acting user's UUID. If the UI needs a
   name→user search, wire it to the admin users endpoint separately.

6. **Error handling** — surface `400` details verbatim (the backend message
   lists valid modules), and show an empty state rather than an error when a
   filter legitimately matches nothing.

---

## 8. Known gaps (not in this API yet)

- **Login / logout / role-assignment events** are recorded by the identity
  service, not core-service, so they do **not** appear in `/admin/audit-logs`
  yet. They will need a separate identity-service integration.
- **Users / Roles modules are sparse** for the same reason (`Users` has only
  `warehouse_users`, `Roles` is empty).
